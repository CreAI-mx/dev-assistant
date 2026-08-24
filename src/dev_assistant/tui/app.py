"""Textual app for the read-only dev-assistant dashboard.

Left: a navigation tree (Overview / Issues / Reviews / Lessons) drilling down
through phases -> subtasks/sub-branches -> rounds -> artifact files. Right: a
ContentSwitcher between a colored structured view (overview, issue timeline,
review rounds) and a raw markdown viewer for individual artifacts.
"""
from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import ContentSwitcher, Footer, Header, Markdown, Static, Tree
from textual.widgets.tree import TreeNode

from . import render, theme
from .gitinfo import GitInfo, load_git_info
from .model import Issue, PhaseStatus, Review, Round, Workspace, load_workspace

KIND_OVERVIEW = "overview"
KIND_ISSUE = "issue"
KIND_REVIEW = "review"
KIND_FILE = "file"


class DashboardApp(App):
    CSS = """
    #nav {
        width: 42;
        min-width: 30;
        border-right: solid $primary;
    }
    Tree { padding: 0 1; }
    #content { padding: 0 1; }
    #struct, #file { padding: 0 1; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("o", "overview", "Overview"),
    ]

    def __init__(self, workspace_root: Path) -> None:
        super().__init__()
        self.workspace_root = workspace_root
        self.workspace: Workspace | None = None
        self.git: GitInfo | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            yield Tree("dev-assistant", id="nav")
            with ContentSwitcher(initial="struct", id="content"):
                with VerticalScroll(id="struct"):
                    yield Static(id="structured")
                with VerticalScroll(id="file"):
                    yield Markdown(id="fileview")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "dev-assistant"
        self._reload()

    # --- data / tree --------------------------------------------------------

    def _reload(self) -> None:
        self.workspace = load_workspace(self.workspace_root)
        self.git = load_git_info(self.workspace.repo_root)
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
            Text("Overview", style="bold"), data={"kind": KIND_OVERVIEW}
        )
        overview.allow_expand = False

        active = ws.active_issues
        issues_node = tree.root.add(_section("Issues", len(active)))
        issues_node.expand()
        for issue in active:
            self._add_issue_node(issues_node, issue)

        archived = ws.archived_issues
        if archived:
            arch_node = tree.root.add(_section("Archived", len(archived)))
            for issue in archived:
                self._add_issue_node(arch_node, issue)

        if ws.reviews:
            reviews_node = tree.root.add(_section("Reviews", len(ws.reviews)))
            reviews_node.expand()
            for review in ws.reviews:
                self._add_review_node(reviews_node, review)

        if ws.lessons:
            lessons_node = tree.root.add(_section("Lessons", len(ws.lessons)))
            for name in ws.lessons:
                lessons_node.add_leaf(
                    name, data={"kind": KIND_FILE, "path": ws.root / "lessons" / name}
                )

    def _add_issue_node(self, parent: TreeNode, issue: Issue) -> None:
        bar = render.progress_bar(issue.completed_count, issue.total_phases)
        state = "complete" if issue.is_complete else (
            issue.current_phase.label if issue.current_phase else "new"
        )
        label = Text()
        label.append(issue.id, style="bold cyan")
        if issue.experimental:
            label.append(" exp", style="yellow")
        label.append(f"  {bar} ", style="green")
        label.append(state, style="dim")
        node = parent.add(label, data={"kind": KIND_ISSUE, "issue": issue})

        for phase in issue.phases:
            if not phase.has_content:
                continue
            self._add_phase_node(node, issue, phase)

        issue_md = issue.path / "issue.md"
        if issue_md.is_file():
            node.add_leaf("issue.md", data={"kind": KIND_FILE, "path": issue_md})

    def _add_phase_node(self, parent: TreeNode, issue: Issue, phase: PhaseStatus) -> None:
        state = issue.phase_state(phase)
        label = Text()
        label.append(f"{theme.state_icon(state)} ", style=theme.state_style(state))
        label.append(phase.label, style="yellow")
        meta = render._phase_meta(phase)
        if meta:
            label.append(f"  {meta}", style="dim")
        phase_node = parent.add(label)

        for fname in phase.files:
            phase_node.add_leaf(
                fname, data={"kind": KIND_FILE, "path": phase.path / fname}
            )
        # Rounds directly under the phase — single-branch / main-PR feedback.
        for rnd in phase.rounds:
            if not rnd.has_content:
                continue
            self._add_round_node(phase_node, rnd)
        for sp in phase.subphases:
            if not sp.has_content:
                continue
            sp_label = Text()
            sp_label.append(sp.name, style="cyan")
            bits = []
            if sp.round_count:
                bits.append(f"{sp.round_count}r")
            if sp.files:
                bits.append(f"{len(sp.files)}f")
            if bits:
                sp_label.append(f"  {' '.join(bits)}", style="dim")
            sp_node = phase_node.add(sp_label)
            for fname in sp.files:
                sp_node.add_leaf(
                    fname, data={"kind": KIND_FILE, "path": sp.path / fname}
                )
            for rnd in sp.rounds:
                self._add_round_node(sp_node, rnd)

    def _add_round_node(self, parent: TreeNode, rnd: Round) -> None:
        """A round node: its flat files, then a node per nested folder
        (`clusters/<id>-<slug>/` on the feedback side, `comments/` on the
        reviewer side)."""
        label = Text(rnd.name, style="yellow")
        if rnd.cluster_count:
            label.append(f"  {rnd.cluster_count}c", style="dim")
        rnode = parent.add(label)
        _add_dir_children(rnode, rnd.path)

    def _add_review_node(self, parent: TreeNode, review: Review) -> None:
        label = Text()
        label.append(f"pr-{review.pr}", style="bold magenta")
        label.append(f"  {review.last_verdict} · r{review.round_count}", style="dim")
        node = parent.add(label, data={"kind": KIND_REVIEW, "review": review})
        for rnd in review.rounds:
            self._add_round_node(node, rnd)
        review_md = review.path / "review.md"
        if review_md.is_file():
            node.add_leaf("review.md", data={"kind": KIND_FILE, "path": review_md})

    # --- rendering ----------------------------------------------------------

    def _show_struct(self, renderable) -> None:
        self.query_one("#structured", Static).update(renderable)
        self.query_one("#content", ContentSwitcher).current = "struct"
        self.query_one("#struct", VerticalScroll).scroll_home(animate=False)

    def _show_overview(self) -> None:
        if self.workspace is None:
            return
        self._show_struct(render.render_overview(self.workspace, git=self.git))

    def _show_file(self, path: Path) -> None:
        try:
            text = path.read_text()
        except OSError as exc:
            self._show_struct(Text(f"Cannot read {path}\n\n{exc}", style="red"))
            return
        md = self.query_one("#fileview", Markdown)
        md.update(text)
        self.query_one("#content", ContentSwitcher).current = "file"
        self.query_one("#file", VerticalScroll).scroll_home(animate=False)

    # --- events / actions ---------------------------------------------------

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        data = event.node.data
        if not data:
            return
        kind = data.get("kind")
        if kind == KIND_OVERVIEW:
            self._show_overview()
        elif kind == KIND_ISSUE:
            self._show_struct(render.render_issue(data["issue"], git=self.git))
        elif kind == KIND_REVIEW:
            self._show_struct(render.render_review(data["review"]))
        elif kind == KIND_FILE:
            self._show_file(data["path"])

    def action_refresh(self) -> None:
        self._reload()
        self.notify("Workspace reloaded", timeout=2)

    def action_overview(self) -> None:
        self._show_overview()


def _add_dir_children(node: TreeNode, path: Path) -> None:
    """Add `path`'s files as leaves and its subfolders as nested nodes."""
    if not path.is_dir():
        return
    children = sorted(path.iterdir(), key=lambda p: (p.is_dir(), p.name))
    for child in children:
        if child.is_file():
            node.add_leaf(child.name, data={"kind": KIND_FILE, "path": child})
        elif child.is_dir() and any(child.iterdir()):  # skip empty scaffolding
            _add_dir_children(node.add(Text(f"{child.name}/", style="magenta")), child)


def _section(name: str, count: int) -> Text:
    label = Text(name, style="bold")
    label.append(f"  {count}", style="dim")
    return label


def run(workspace_root: Path) -> None:
    DashboardApp(workspace_root).run()
