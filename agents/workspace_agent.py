"""
Document Editor Workspace Agent: the chat-driven editing loop behind the split-screen UI.

  user message -> Edit Intent Parser (Gemini or rules) -> validated JSON commands
  -> deterministic DOCX/PPTX editor -> new file + version -> preview + chat reply
"""
import os
import re
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents import workspace_store as store
from agents.edit_intent_parser import parse_edit_request
from agents.edit_rule_parser import ParseContext
from agents.edit_rules_vocab import ORDINALS
from agents.workspace_edit import apply_commands, build_preview, outline, validate_selection
from core.edit_schema import ClarificationNeeded, EditError
from core.ooxml_package import PackageError, image_info
from core.version_manager import VersionManager

MAX_MESSAGE_CHARS = 2000
CHOICE_RE = re.compile(r"^\s*(?:option\s*|number\s*|#)?(\d+)\s*[.)]?\s*$", re.I)
EXAMPLES = {"docx": "“Change the title font to Arial and make it bold” or “Remove the paragraph about …”",
            "pptx": "“Change the title on slide 1 to Arial, 32 points” or “Remove the third bullet from slide 2”"}


def sentence(text: str) -> str:
    """Ends text with a full stop unless it already ends with punctuation (possibly inside a quote)."""
    return text if text.rstrip("”\"'").endswith((".", "!", "?")) else text + "."


def copy_atomic(source: Path, target: Path) -> None:
    """Copy-then-rename, so an interrupted undo can't leave a half-written document."""
    tmp = target.with_name(target.name + ".tmp")
    shutil.copy2(source, tmp)
    os.replace(tmp, target)


class WorkspaceAgent:
    def __init__(self):
        self.name = "Document Editor Agent"
        self.state = store.load_state()

    # ---------- state ----------
    def versions(self) -> Optional[VersionManager]:
        active = self.state["active"]
        return VersionManager(active["versions_dir"]) if active else None

    def snapshot(self, include_preview: bool = True, preview: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        active = self.state["active"]
        result: Dict[str, Any] = {"messages": self.state["messages"], "active": None, "preview": None, "versions": [],
                                  "pending_image": self.state["pending_image"],
                                  "parser": "gemini" if os.environ.get("GEMINI_API_KEY", "").strip()
                                  and os.environ.get("EDIT_PARSER", "auto") != "rules" else "rules"}
        if not active:
            return result
        history = self.versions().get_history()  # type: ignore[union-attr]
        index = active["version_index"]
        result["versions"] = [{"version": v["version"], "instruction": v["instruction"], "timestamp": v["timestamp"],
                               "changes": v["diff_summary"]} for v in history]
        result["active"] = {"name": active["name"], "type": active["type"], "version": history[index]["version"],
                            "version_index": index, "can_undo": index > 0, "can_redo": index < len(history) - 1}
        if include_preview:
            result["preview"] = preview or build_preview(store.working_path(active).read_bytes(), active["type"])
        return result

    def respond(self, status: str, preview: Optional[Dict[str, Any]] = None, **extra: Any) -> Dict[str, Any]:
        store.save_state(self.state)
        return {"status": status, **extra, "state": self.snapshot(preview=preview)}

    # ---------- opening files ----------
    def open(self, user_path: str) -> Dict[str, Any]:
        source = store.safe_document_path(user_path)
        doc_type = store.DOC_EXTENSIONS[source.suffix.lower()]
        folder = store.new_artifact_dir(source.name)
        target = folder / source.name
        shutil.copy2(source, target)
        try:
            preview = build_preview(target.read_bytes(), doc_type)
        except (PackageError, KeyError, ValueError) as e:
            shutil.rmtree(folder, ignore_errors=True)
            raise EditError(f"I couldn't read {source.name}. It may be corrupted or not a real {doc_type.upper()} file.") from e
        versions = VersionManager(str(folder / "versions"))
        versions.snapshot_file(f"Opened {source.name}", str(target), author=self.name, changes=[f"Opened {source.name}"])
        self.state.update({"active": {"name": source.name, "type": doc_type, "working_path": store.relative(target),
                                      "versions_dir": store.relative(folder / "versions"), "version_index": 0},
                           "messages": [], "pending_choices": None, "last_target": None})
        size = f"{len(preview['slides'])} slides" if doc_type == "pptx" else f"{len(preview['blocks'])} blocks"
        store.add_message(self.state, "assistant", f"Opened {source.name} ({size}) as v1.0. Tell me what to change, "
                          f"for example {EXAMPLES[doc_type]}. You can also click an item in the preview and say “this”.",
                          status="info")
        return self.respond("ok", preview=preview)

    def attach_image(self, user_path: str) -> Dict[str, Any]:
        path = store.safe_upload_path(user_path)
        data = path.read_bytes()
        if len(data) > store.MAX_IMAGE_BYTES:
            raise EditError("That image is larger than 5 MB. Please upload a smaller logo.")
        try:
            _, width, height = image_info(data)
        except ValueError as e:
            raise EditError(str(e)) from e
        self.state["pending_image"] = {"path": store.relative(path), "name": path.name, "width": width, "height": height}
        store.add_message(self.state, "assistant", f"Got {path.name} ({width}×{height} px). Now say “Replace the company "
                          "logo with the uploaded image”.", status="info")
        return self.respond("ok")

    def upload(self, user_path: str) -> Dict[str, Any]:
        suffix = Path(user_path).suffix.lower()
        if suffix in store.DOC_EXTENSIONS:
            return self.open(user_path)
        if suffix in store.IMAGE_EXTENSIONS:
            return self.attach_image(user_path)
        raise EditError("The editor accepts .docx, .pptx and images (.png, .jpg, .gif).")

    # ---------- chat ----------
    def chat(self, message: str, selection: Any = None, current_slide: Any = 1) -> Dict[str, Any]:
        active = self.state["active"]
        message = (message or "").strip()
        if not active:
            raise EditError("Open a document first: pick one on the right or upload a .docx / .pptx.")
        if not message:
            raise EditError("Type an instruction first.")
        if len(message) > MAX_MESSAGE_CHARS:
            raise EditError(f"That message is too long (max {MAX_MESSAGE_CHARS} characters).")
        slide = current_slide if isinstance(current_slide, int) and current_slide > 0 else 1
        clean_selection = validate_selection(selection)
        history = [{"role": m["role"], "text": m["text"]} for m in self.state["messages"][-6:]]
        store.add_message(self.state, "user", message)

        commands, parser, note = self.pick_choice(message), "choice", None
        if commands is None:
            path = store.working_path(active)
            ctx = ParseContext(doc_type=active["type"], selection_kind=(clean_selection or {}).get("kind"),
                               current_slide=slide, last_target=self.state.get("last_target"),
                               outline=outline(path.read_bytes(), active["type"]), history=history)
            result = parse_edit_request(message, ctx)
            parser, note = result.parser, result.note
            if result.clarification:
                self.state["pending_choices"] = None
                store.add_message(self.state, "assistant", result.clarification, status="clarify", parser=parser, note=note)
                return self.respond("clarify")
            commands = result.commands
        self.state["pending_choices"] = None
        return self.apply(message, commands, clean_selection, slide, parser, note)

    def pick_choice(self, message: str) -> Optional[List[Dict[str, Any]]]:
        """Maps '2' / 'the second one' / 'option 2' onto a pending clarification option."""
        pending = self.state.get("pending_choices")
        if not pending:
            return None
        match = CHOICE_RE.match(message)
        words = re.findall(r"[a-z0-9]+", message.lower())
        number = int(match.group(1)) if match else next((ORDINALS[w] for w in words if w in ORDINALS), None)
        options = pending["options"]
        if number == -1:
            number = len(options)
        if number is None or not 1 <= number <= len(options) or (not match and len(words) > 4):
            return None
        return options[number - 1]["commands"]

    def apply(self, message: str, commands: List[Dict[str, Any]], selection: Optional[Dict[str, Any]], slide: int,
              parser: str, note: Optional[str]) -> Dict[str, Any]:
        active = self.state["active"]
        try:
            validated, outcomes, changed, preview = apply_commands(
                store.working_path(active), active["type"], commands, selection, slide,
                store.pending_image_bytes(self.state))
        except ClarificationNeeded as c:
            options = [{"label": o["label"], "commands": commands[:c.command_index] + [o["command"]]
                        + commands[c.command_index + 1:]} for o in c.options]
            self.state["pending_choices"] = {"options": options} if options else None
            store.add_message(self.state, "assistant", c.question, status="clarify", parser=parser, note=note,
                              options=[o["label"] for o in options], commands=commands)
            return self.respond("clarify")
        except (EditError, PackageError) as e:
            store.add_message(self.state, "assistant", f"I couldn't make that change: {e} The document was not modified.",
                              status="error", parser=parser, note=note, commands=commands)
            return self.respond("error")

        versions = self.versions()
        if versions is None:
            raise EditError('Open a document first.')
        summaries = [o.summary for o in outcomes]
        previous = Path(versions.get_history()[active["version_index"]]["file_path"])
        try:
            versions.truncate(active["version_index"] + 1)
            record = versions.snapshot_file(message, str(store.working_path(active)), author=self.name, changes=summaries)
        except OSError:
            # The edit is only kept if it is also recorded as a version; otherwise roll the file back
            copy_atomic(previous, store.working_path(active))
            raise
        active["version_index"] = len(versions.get_history()) - 1
        self.state["last_target"] = next((c["target"] for c in reversed(validated) if c.get("target")), None)
        reply = sentence("Done. I " + ", and ".join(summaries))
        store.add_message(self.state, "assistant", reply, status="done", parser=parser, note=note,
                          commands=validated, version=record["version"], changed=changed)
        return self.respond("done", preview=preview, changed=changed)

    # ---------- versions ----------
    def restore(self, index: int, verb: str) -> Dict[str, Any]:
        active = self.state["active"]
        versions = self.versions()
        if not active or versions is None:
            raise EditError("Open a document first.")
        history = versions.get_history()
        if not 0 <= index < len(history):
            raise EditError("Nothing to undo." if verb == "Undid" else "Nothing to redo." if verb == "Redid" else "Unknown version.")
        source = Path(history[index]["file_path"])
        if not source.is_file():
            raise EditError(f"The file for {history[index]['version']} is missing.")
        undone = history[active["version_index"]]
        copy_atomic(source, store.working_path(active))
        active["version_index"] = index
        self.state["pending_choices"] = None
        what = f"“{undone['instruction']}”" if verb == "Undid" else f"“{history[index]['instruction']}”"
        text = f"{sentence(verb + ' ' + what)} The document is now at {history[index]['version']}." if verb != "Restored" else \
            f"Restored {history[index]['version']} ({history[index]['instruction']})."
        store.add_message(self.state, "assistant", text, status="info", version=history[index]["version"])
        return self.respond("ok")

    def undo(self) -> Dict[str, Any]:
        return self.restore((self.state["active"] or {}).get("version_index", 0) - 1, "Undid")

    def redo(self) -> Dict[str, Any]:
        return self.restore((self.state["active"] or {}).get("version_index", 0) + 1, "Redid")

    def restore_version(self, version: str) -> Dict[str, Any]:
        versions = self.versions()
        history = versions.get_history() if versions else []
        index = next((i for i, v in enumerate(history) if v["version"] == version), -1)
        return self.restore(index, "Restored")

    def clear(self) -> Dict[str, Any]:
        self.state.update({"messages": [], "pending_choices": None, "last_target": None})
        return self.respond("ok")


def run_workspace(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Entry point for run_pipeline.py. Never raises: problems become a friendly error reply."""
    agent = WorkspaceAgent()
    op = payload.get("op")
    try:
        if op == "state":
            return {"status": "ok", "state": agent.snapshot()}
        if op == "list":
            return {"status": "ok", "artifacts": store.list_artifacts()}
        if op == "open":
            return agent.open(str(payload.get("path", "")))
        if op == "upload":
            return agent.upload(str(payload.get("path", "")))
        if op == "chat":
            return agent.chat(str(payload.get("message", "")), payload.get("selection"), payload.get("current_slide"))
        if op in ("undo", "redo", "clear"):
            return getattr(agent, op)()
        if op == "restore":
            return agent.restore_version(str(payload.get("version", "")))
        return {"status": "error", "error": f"Unknown workspace operation '{op}'."}
    except (EditError, PackageError) as e:
        return {"status": "error", "error": str(e)}
    except OSError:
        traceback.print_exc(file=sys.stderr)
        return {"status": "error", "error": "The file could not be saved (disk or permission problem). The last saved version is unchanged."}
    except Exception:  # last line of defence: log the details for developers, show a safe message
        traceback.print_exc(file=sys.stderr)
        return {"status": "error", "error": "Something went wrong while handling that request. The document was not changed."}
