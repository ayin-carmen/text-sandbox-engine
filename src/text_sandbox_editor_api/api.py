"""FastAPI application for the local editor process."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .service import EditorService, RevisionConflict


class WorkspaceOpen(BaseModel):
    root: str


class SceneDocument(BaseModel):
    document: dict[str, Any]
    revision: str | None = None


class EntityDocument(BaseModel):
    document: dict[str, Any]
    revision: str | None = None


class EntityTemplateRequest(BaseModel):
    entity_type: str = Field(alias="type")
    namespace: str
    slug: str
    name: str = ""
    tags: list[str] = Field(default_factory=list)
    location: str | None = None
    template: str = "basic"
    preview: bool = False


class SceneTemplateRequest(BaseModel):
    name: str = ""
    namespace: str
    slug: str
    location: str
    template_id: str = Field(alias="template")
    repeat_policy: str = "always"
    priority: int = 0
    preview: bool = False


class SceneName(BaseModel):
    new_scene_id: str
    revision: str


class SessionCommand(BaseModel):
    command: dict[str, Any]


class CandidateRequest(BaseModel):
    session_id: str | None = None
    actor: str = "actor.player"


class StateDiffRequest(BaseModel):
    before: dict[str, Any]
    after: dict[str, Any]


class ChangedByRequest(BaseModel):
    trace: dict[str, Any]
    path: str


def create_app(service: EditorService | None = None) -> FastAPI:
    editor = service or EditorService()
    app = FastAPI(title="Text Sandbox Editor API", version="0.1.0")
    app.state.editor_service = editor
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "tauri://localhost"], allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(RevisionConflict)
    async def revision_conflict_handler(_, exc: RevisionConflict):
        return _error(409, "editor.external_conflict", str(exc))

    @app.post("/api/workspaces/open")
    def open_workspace(payload: WorkspaceOpen):
        return editor.open_workspace(payload.root)

    @app.get("/api/workspaces/current")
    def current_workspace():
        return editor.current_workspace()

    @app.get("/api/workspaces/tree")
    def workspace_tree():
        return editor.tree()

    @app.post("/api/workspaces/refresh")
    def refresh_workspace():
        return editor.refresh()

    @app.get("/api/workspaces/state")
    def source_state():
        return editor.source_state()

    @app.get("/api/metadata/entity-types")
    def entity_types():
        return editor.entity_types()

    @app.get("/api/metadata/entity-templates")
    def entity_templates():
        return editor.entity_templates()

    @app.get("/api/world/entities")
    def list_entities(entity_type: str | None = Query(default=None, alias="type"), query: str | None = None):
        return editor.entities(entity_type, query)

    @app.get("/api/world/entities/{entity_id}")
    def get_entity(entity_id: str):
        try:
            return editor.entity(entity_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/world/entities/{entity_id}/usages")
    def entity_usages(entity_id: str):
        return editor.entity_usages(entity_id)

    @app.post("/api/validation/world-state")
    def validate_world_state():
        return editor.validate_world_state()

    @app.post("/api/world/entities/from-template")
    def entity_from_template(payload: EntityTemplateRequest):
        try:
            return editor.entity_from_template(
                entity_type=payload.entity_type,
                namespace=payload.namespace,
                slug=payload.slug,
                name=payload.name,
                tags=payload.tags,
                location=payload.location,
                template_id=payload.template,
                preview=payload.preview,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/world/entities")
    def create_entity(payload: EntityDocument):
        try:
            return editor.create_entity(payload.document)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.put("/api/world/entities/{entity_id}")
    def save_entity(entity_id: str, payload: EntityDocument):
        if not payload.revision:
            raise HTTPException(422, "revision is required")
        try:
            return editor.save_entity(entity_id, payload.document, payload.revision)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.delete("/api/world/entities/{entity_id}")
    def delete_entity(entity_id: str, revision: str):
        try:
            return editor.delete_entity(entity_id, revision)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        except RevisionConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/content/scenes")
    def list_scenes():
        return {"scenes": editor.scenes()}

    @app.get("/api/content/scenes/{scene_id:path}")
    def get_scene(scene_id: str):
        return editor.scene(scene_id)

    @app.post("/api/content/scenes")
    def create_scene(payload: SceneDocument):
        try:
            return editor.create_scene(payload.document)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/metadata/scene-templates")
    def scene_templates():
        return editor.scene_templates()

    @app.post("/api/content/scenes/from-template")
    def scene_from_template(payload: SceneTemplateRequest):
        try:
            return editor.scene_from_template(
                name=payload.name,
                namespace=payload.namespace,
                slug=payload.slug,
                location=payload.location,
                template_id=payload.template_id,
                repeat_policy=payload.repeat_policy,
                priority=payload.priority,
                preview=payload.preview,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.put("/api/content/scenes/{scene_id:path}")
    def save_scene(scene_id: str, payload: SceneDocument):
        if not payload.revision:
            raise HTTPException(422, "revision is required")
        try:
            return editor.save_scene(scene_id, payload.document, payload.revision)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.delete("/api/content/scenes/{scene_id:path}")
    def delete_scene(scene_id: str, revision: str):
        try:
            return editor.delete_scene(scene_id, revision)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        except RevisionConflict as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/api/content/scenes/{scene_id:path}/duplicate")
    def duplicate_scene(scene_id: str, payload: SceneName):
        try:
            return editor.duplicate_scene(scene_id, payload.new_scene_id, payload.revision)
        except (KeyError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/content/scenes/{scene_id:path}/rename")
    def rename_scene(scene_id: str, payload: SceneName):
        try:
            return editor.rename_scene(scene_id, payload.new_scene_id, payload.revision)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        except RevisionConflict as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/metadata/registry")
    def registry_metadata():
        return editor.registry_metadata()

    @app.get("/api/metadata/references")
    def references(reference_type: str | None = Query(default=None, alias="type")):
        return editor.references(reference_type)

    @app.get("/api/metadata/schemas")
    def schemas():
        return editor.schemas()

    @app.post("/api/validation/content")
    def validate_content():
        return editor.validate_content()

    @app.post("/api/validation/document")
    def validate_document(payload: SceneDocument):
        return editor.validate_document(payload.document, None)

    @app.get("/api/graph/content")
    def graph_content():
        return editor.graph()

    @app.post("/api/runtime/sessions")
    def create_session():
        return editor.create_session()

    @app.post("/api/runtime/sessions/{session_id}/commands")
    def execute_command(session_id: str, payload: SessionCommand):
        try:
            return editor.session_command(session_id, payload.command)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/runtime/sessions/{session_id}/state")
    def session_state(session_id: str):
        try:
            return editor.session_state(session_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/api/runtime/sessions/{session_id}/actions")
    def session_actions(session_id: str, actor: str = "actor.player"):
        try:
            return editor.session_actions(session_id, actor)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/api/runtime/sessions/{session_id}/reset")
    def reset_session(session_id: str):
        try:
            return editor.reset_session(session_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/api/diagnostics/scene-candidates")
    def scene_candidates(payload: CandidateRequest):
        return editor.candidate_report(payload.session_id, payload.actor)

    @app.post("/api/diagnostics/state-diff")
    def state_diff(payload: StateDiffRequest):
        return editor.state_diff(payload.before, payload.after)

    @app.post("/api/diagnostics/changed-by")
    def changed_by(payload: ChangedByRequest):
        return {"matches": editor.changed_by(payload.trace, payload.path)}

    return app


def _error(status: int, code: str, message: str):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


app = create_app()
