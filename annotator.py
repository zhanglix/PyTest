
import sublime

from . import formatters


STYLESHEET = '''
    <style>
        div.error {
            padding: 0rem 0.7rem 0.4rem 0rem;
            margin: 0.2rem 0;
            border-radius: 2px;
            position: relative;
        }

        span.message {
            padding-right: 0.7rem;
        }
    </style>
'''


class Annotator:
    def __init__(self):
        self._last_errors = None

    def annotate(self, view, errors={}, mode='auto', running=False,
                 **_):
        if errors != self._last_errors:
            # reset 'local' state
            self._drawn = set()
            self._phantom_sets_by_buffer = {}
            self._last_errors = errors

        buffer_id = view.buffer_id()
        if buffer_id in self._drawn:
            return

        errs = get_errors_for_view(view, errors)
        if errs is None:
            # As long the tests are still running, we just don't know if
            # the view really is clean. To reduce visual clutter, we return
            # immediately.
            if running:
                return
            view.erase_regions('PyTestRunner')
            self._drawn.add(buffer_id)
            return

        self._draw_regions(view, errs)
        self._draw_phantoms(view, errs, mode)
        self._drawn.add(buffer_id)

    def _draw_regions(self, view, errs):
        regions = [view.full_line(view.text_point(tbck['line'] - 1, 0))
                   for tbck in errs]

        view.erase_regions('PyTestRunner')
        view.add_regions('PyTestRunner', regions,
                         'markup.deleted.diff',
                         'bookmark',
                         sublime.DRAW_OUTLINED)

    def _draw_phantoms(self, view, errs, mode='auto'):
        formatter = formatters.TB_MODES[mode]
        phantoms = []

        for tbck in errs:
            line = tbck['line']
            text = tbck['text']

            pt = view.text_point(line - 1, 0)
            indentation = get_indentation_at(view, pt)

            if text == '':
                continue
            text = formatter.format_text(text, indentation)

            phantoms.append(sublime.Phantom(
                sublime.Region(pt, view.line(pt).b),
                ('<body id=inline-error>' + STYLESHEET +
                    '<div class="error">' +
                    '<span class="message">' + text + '</span>' +
                    '</div>' +
                    '</body>'),
                sublime.LAYOUT_BELOW))

        buffer_id = view.buffer_id()
        if buffer_id not in self._phantom_sets_by_buffer:
            phantom_set = sublime.PhantomSet(view, "exec")
            self._phantom_sets_by_buffer[buffer_id] = phantom_set
        else:
            phantom_set = self._phantom_sets_by_buffer[buffer_id]

        phantom_set.update(phantoms)


    def annotate_visible_views(self, **kwargs):
        window = sublime.active_window()

        views = [window.active_view_in_group(group)
                 for group in range(window.num_groups())]

        for view in views:
            self.annotate(view, **kwargs)


def get_errors_for_view(view, errors_by_view):
    # type: (View, Dict[Filename, Tracebacks]) -> Optional[Tracebacks]
    """Return errors for a given view or None."""

    window = view.window()
    for file, tracebacks in errors_by_view.items():
        if view == window.find_open_file(file):
            return tracebacks


def get_indentation_at(view, pt):
    # type: (View, Point) -> int
    """Return the indentation level as an int given a view and a point"""

    line = view.substr(view.line(pt))
    return len(line) - len(line.lstrip(' '))

