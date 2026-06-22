"""Textual app for the read-only dev-assistant dashboard.

Left: a navigation tree (Overview / Issues / Reviews / Lessons) that drills down
to individual artifact files. Right: a single Markdown pane that renders either a
synthesized detail view or a raw artifact file — the `glow` replacement.
"""
from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Header, Markdown, Tree
from textual.widgets.tree import TreeNode

from . import render
from .model import Issue, Review, Workspace, load_workspace

# Node payload kinds.
KIND_OVERVIEW = "overview"
KIND_ISSUE = "issue"
KIND_REVIEW = "review"
KIND_FILE = "file"
KIND_GROUP = "group"


class DashboardApp(App):
    CSS = """
    Screen {
        layout: horizontal;
    }
    #nav {
        width: 38;
        min-width: 28;
        border-right: solid $primary;
    }
    #content {
        padding: 0 1;
    }
    Tree {
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("o", "overview", "Overview"),
        Binding("e", "toggle_expand", "Expand/Collapse"),
    ]

    def __init__(self, workspace_root: Path) -> None:
        super().__init__()
        self.workspace_root = workspace_root
        self.workspace: Workspace | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            yield Tree("dev-assistant", id="nav")
            with VerticalScroll(id="content"):
                yield Markdown("# Loading…", id="detail")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "dev-assistant"
        self._reload()

    # --- data / tree construction ------------------------------------------

    def _reload(self) -> None:
        self.workspace = load_workspace(self.workspace_root)
        self.sub_title = f"{self.workspace.repo_name}  ·  {self.workspace.root}"
        tree = self.query_one("#nav", Tree)
        tree.clear()
        self._build_tree(tree)
        tree.root.expand()
        self._show_overview()

    def _build_tree(self, tree: Tree) -> None:
        ws = self.workspace
        assert ws is not None

        overview = tree.root.add(
            Text.from_markup("[bold]📊 Overview[/]"), data={"kind": KIND_OVERVIEW}
        )
        overview.allow_expand = False

        active = ws.active_issues
        issues_node = tree.root.add(
            Text.from_markup(f"[bold]📋 Issues[/] [dim]({len(active)} active)[/]")
        )
        issues_node.expand()
        for issue in active:
            self._add_issue_node(issues_node, issue)

        archived = ws.archived_issues
        if archived:
            arch_node = tree.root.add(
                Text.from_markup(f"[bold]📦 Archived[/] [dim]({len(archived)})[/]")
            )
            for issue in archived:
                self._add_issue_node(arch_node, issue)

        if ws.reviews:
            reviews_node = tree.root.add(
                Text.from_markup(f"[bold]🔍 Reviews[/] [dim]({len(ws.reviews)})[/]")
            )
            reviews_node.expand()
            for review in ws.reviews:
                self._add_review_node(reviews_node, review)

        if ws.lessons:
            lessons_node = tree.root.add(
                Text.from_markup(f"[bold]📚 Lessons[/] [dim]({len(ws.lessons)})[/]")
            )
            for name in ws.lessons:
                lessons_node.add_leaf(
                    name,
                    data={"kind": KIND_FILE, "path": ws.root / "lessons" / name},
                )

    def _add_issue_node(self, parent: TreeNode, issue: Issue) -> None:
        bar = render.progress_bar(issue.completed_count, issue.total_phases)
        cur = "done" if issue.is_complete else (
            issue.current_phase.label if issue.current_phase else "new"
        )
        flag = " ⚗️" if issue.experimental else ""
        label = Text.from_markup(
            f"[bold cyan]{_esc(issue.id)}[/]{flag}  [green]{bar}[/] [dim]{cur}[/]"
        )
        node = parent.add(label, data={"kind": KIND_ISSUE, "issue": issue})
        for phase in issue.phases:
            if not phase.files:
                continue
            phase_node = node.add(
                Text.from_markup(f"[yellow]{phase.name}[/] [dim]({len(phase.files)})[/]")
            )
            for fname in phase.files:
                phase_node.add_leaf(
                    fname,
                    data={"kind": KIND_FILE, "path": issue.path / phase.name / fname},
                )
        # The issue.md itself.
        issue_md = issue.path / "issue.md"
        if issue_md.is_file():
            node.add_leaf(
                "issue.md", data={"kind": KIND_FILE, "path": issue_md}
            )

    def _add_review_node(self, parent: TreeNode, review: Review) -> None:
        label = Text.from_markup(
            f"[bold magenta]pr-{_esc(review.pr)}[/]  [dim]{_esc(review.last_verdict)} "
            f"· r{review.rounds}[/]"
        )
        node = parent.add(label, data={"kind": KIND_REVIEW, "review": review})
        # List round folders and their files.
        for round_dir in sorted(
            p for p in review.path.iterdir() if p.is_dir() and p.name.startswith("round-")
        ):
            round_node = node.add(Text.from_markup(f"[yellow]{round_dir.name}[/]"))
            for f in sorted(round_dir.rglob("*.md")):
                rel = f.relative_to(round_dir)
                round_node.add_leaf(
                    str(rel), data={"kind": KIND_FILE, "path": f}
                )
        review_md = review.path / "review.md"
        if review_md.is_file():
            node.add_leaf("review.md", data={"kind": KIND_FILE, "path": review_md})

    # --- rendering ----------------------------------------------------------

    def _detail(self) -> Markdown:
        return self.query_one("#detail", Markdown)

    def _show_overview(self) -> None:
        if self.workspace is None:
            return
        self._detail().update(render.render_overview(self.workspace))
        self.query_one("#content").scroll_home(animate=False)

    def _show_markdown(self, text: str) -> None:
        self._detail().update(text)
        self.query_one("#content").scroll_home(animate=False)

    def _show_file(self, path: Path) -> None:
        try:
            text = path.read_text()
        except OSError as exc:
            self._show_markdown(f"# Cannot read file\n\n`{path}`\n\n```\n{exc}\n```")
            return
        self._show_markdown(text)

    # --- events / actions ---------------------------------------------------

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        data = event.node.data
        if not data:
            return
        kind = data.get("kind")
        if kind == KIND_OVERVIEW:
            self._show_overview()
        elif kind == KIND_ISSUE:
            self._show_markdown(render.render_issue(data["issue"]))
        elif kind == KIND_REVIEW:
            self._show_markdown(render.render_review(data["review"]))
        elif kind == KIND_FILE:
            self._show_file(data["path"])

    def action_refresh(self) -> None:
        self._reload()
        self.notify("Workspace reloaded", timeout=2)

    def action_overview(self) -> None:
        self._show_overview()

    def action_toggle_expand(self) -> None:
        node = self.query_one("#nav", Tree).cursor_node
        if node is None or not node.allow_expand:
            return
        node.toggle()


def _esc(value: str) -> str:
    """Escape Rich markup brackets in dynamic text."""
    return value.replace("[", "\\[")


def run(workspace_root: Path) -> None:
    DashboardApp(workspace_root).run()
