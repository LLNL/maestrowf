"""
Uses rich tree view example to render a view of maestro study workspaces
for the documentation

Todo
----
- [X] Obfuscate abs paths to hide user/machine name info
- [X] Add argparse opts to control output settings
- [ ] Tweak theme to better match mkdocs material dark? the tree branches
      are a little bright
- [X] Explore custom svg format (rich _export_format.py) to remove hard coded
      font and line heights to inherit from mkdocs css settings
      NOTE: something doesn't quite work right -> size 12 renders larger than
      both the size 20 default and size 16 when read in by mkdocs..
- [ ] Custom sizing to remove terminal width dependency for better
      reproducibility
- [ ] Make an svg renderer for status layouts
- [ ] Store these in the docs and make better org for the assets/scripts
"""
import argparse
import os
import pathlib
import sys

# Override the svg export style template
MKDOCS_CONSOLE_SVG_FORMAT = """\
<svg class="rich-terminal" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
    <!-- Generated with Rich https://www.textualize.io -->
    <style>
    @font-face {{
        font-family: "Fira Code";
        src: local("FiraCode-Regular"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff2/FiraCode-Regular.woff2") format("woff2"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff/FiraCode-Regular.woff") format("woff");
        font-style: normal;
        font-weight: 400;
    }}
    @font-face {{
        font-family: "Fira Code";
        src: local("FiraCode-Bold"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff2/FiraCode-Bold.woff2") format("woff2"),
                url("https://cdnjs.cloudflare.com/ajax/libs/firacode/6.2.0/woff/FiraCode-Bold.woff") format("woff");
        font-style: bold;
        font-weight: 700;
    }}
    .{unique_id}-matrix {{
        font-family: Fira Code, monospace;
        font-size: {char_height};
        line-height: {line_height};
        font-variant-east-asian: full-width;
    }}
    .{unique_id}-title {{
        font-size: {char_height};
        font-weight: bold;
        font-family: arial;
    }}
    {styles}
    </style>
    <defs>
    <clipPath id="{unique_id}-clip-terminal">
      <rect x="0" y="0" width="{terminal_width}" height="{terminal_height}" />
    </clipPath>
    {lines}
    </defs>
    {chrome}
    <g transform="translate({terminal_x}, {terminal_y})" clip-path="url(#{unique_id}-clip-terminal)">
    {backgrounds}
    <g class="{unique_id}-matrix">
    {matrix}
    </g>
    </g>
</svg>
""" # noqa E501
from rich import _export_format
_export_format.CONSOLE_SVG_FORMAT = MKDOCS_CONSOLE_SVG_FORMAT

from rich._export_format import CONSOLE_SVG_FORMAT
# CONSOLE_SVG_FORMAT = MKDOCS_CONSOLE_SVG_FORMAT

# Why does flake8 not like this import?a
from rich import print          # noqa E999
from rich.color import parse_rgb_hex, blend_rgb
from rich.console import Console
from rich.filesize import decimal
from rich.markup import escape
from rich.terminal_theme import TerminalTheme, SVG_EXPORT_THEME
from rich.text import Text
from rich.tree import Tree
from rich.segment import Segment
from rich.style import Style

from typing import Optional, Dict, List
import zlib
from math import ceil
from rich.traceback import install
install(show_locals=True)


# Override svg export to change char height/width units from pixels to em
def export_svg(
    self,
    *,
    title: str = "Rich",
    theme: Optional[TerminalTheme] = None,
    clear: bool = True,
    code_format: str = CONSOLE_SVG_FORMAT,
        char_height: int = 16,
) -> str:
    """
    Generate an SVG from the console contents (requires record=True in Console constructor).
    Args:
        path (str): The path to write the SVG to.
        title (str): The title of the tab in the output image
        theme (TerminalTheme, optional): The ``TerminalTheme`` object to use to style the terminal
        clear (bool, optional): Clear record buffer after exporting. Defaults to ``True``
        code_format (str): Format string used to generate the SVG. Rich will inject a number of variables
            into the string in order to form the final SVG output. The default template used and the variables
            injected by Rich can be found by inspecting the ``console.CONSOLE_SVG_FORMAT`` variable.
    """ # noqa E501

    from rich.cells import cell_len

    style_cache: Dict[Style, str] = {}

    def get_svg_style(style: Style) -> str:
        """Convert a Style to CSS rules for SVG."""
        if style in style_cache:
            return style_cache[style]
        css_rules = []
        color = (
            _theme.foreground_color
            if (style.color is None or style.color.is_default)
            else style.color.get_truecolor(_theme)
        )
        bgcolor = (
            _theme.background_color
            if (style.bgcolor is None or style.bgcolor.is_default)
            else style.bgcolor.get_truecolor(_theme)
        )
        if style.reverse:
            color, bgcolor = bgcolor, color
        if style.dim:
            color = blend_rgb(color, bgcolor, 0.4)
        css_rules.append(f"fill: {color.hex}")
        if style.bold:
            css_rules.append("font-weight: bold")
        if style.italic:
            css_rules.append("font-style: italic;")
        if style.underline:
            css_rules.append("text-decoration: underline;")
        if style.strike:
            css_rules.append("text-decoration: line-through;")

        css = ";".join(css_rules)
        style_cache[style] = css
        return css

    _theme = theme or SVG_EXPORT_THEME

    width = self.width
    # char_height = 20
    char_width = char_height * 0.61
    line_height = char_height * 1.22

    margin_top = 1
    margin_right = 1
    margin_bottom = 1
    margin_left = 1

    padding_top = 40
    padding_right = 8
    padding_bottom = 8
    padding_left = 8

    padding_width = padding_left + padding_right
    padding_height = padding_top + padding_bottom
    margin_width = margin_left + margin_right
    margin_height = margin_top + margin_bottom

    text_backgrounds: List[str] = []
    text_group: List[str] = []
    classes: Dict[str, int] = {}
    style_no = 1

    def escape_text(text: str) -> str:
        """HTML escape text and replace spaces with nbsp."""
        return escape(text).replace(" ", "&#160;")

    def make_tag(
        name: str, content: Optional[str] = None, **attribs: object
    ) -> str:
        """Make a tag from name, content, and attributes."""

        def stringify(value: object) -> str:
            if isinstance(value, (float)):
                return format(value, "g")
            return str(value)

        tag_attribs = " ".join(
            f'{k.lstrip("_").replace("_", "-")}="{stringify(v)}"'
            for k, v in attribs.items()
        )
        return (
            f"<{name} {tag_attribs}>{content}</{name}>"
            if content
            else f"<{name} {tag_attribs}/>"
        )

    with self._record_buffer_lock:
        segments = list(Segment.filter_control(self._record_buffer))
        if clear:
            self._record_buffer.clear()

    unique_id = "terminal-" + str(
        zlib.adler32(
            ("".join(segment.text for segment in segments)).encode(
                "utf-8", "ignore"
            )
            + title.encode("utf-8", "ignore")
        )
    )
    y = 0
    segments = Segment.split_and_crop_lines(segments, length=width)
    for y, line in enumerate(segments):
        x = 0
        for text, style, _control in line:
            style = style or Style()
            rules = get_svg_style(style)
            if rules not in classes:
                classes[rules] = style_no
                style_no += 1
            class_name = f"r{classes[rules]}"

            if style.reverse:
                has_background = True
                background = (
                    _theme.foreground_color.hex
                    if style.color is None
                    else style.color.get_truecolor(_theme).hex
                )
            else:
                bgcolor = style.bgcolor
                has_background = bgcolor is not None and not bgcolor.is_default
                background = (
                    _theme.background_color.hex
                    if style.bgcolor is None
                    else style.bgcolor.get_truecolor(_theme).hex
                )

            text_length = cell_len(text)
            if has_background:
                text_backgrounds.append(
                    make_tag(
                        "rect",
                        fill=background,
                        x=x * char_width,
                        y=y * line_height + 1.5,
                        width=char_width * text_length,
                        height=line_height + 0.25,
                        shape_rendering="crispEdges",
                    )
                )

            if text != " " * len(text):
                text_group.append(
                    make_tag(
                        "text",
                        escape_text(text),
                        _class=f"{unique_id}-{class_name}",
                        x=x * char_width,
                        y=y * line_height + char_height,
                        textLength=char_width * len(text),
                        clip_path=f"url(#{unique_id}-line-{y})",
                    )
                )
            x += cell_len(text)

    line_offsets = [line_no * line_height + 1.5 for line_no in range(y)]
    lines = "\n".join(
        f"""<clipPath id="{unique_id}-line-{line_no}">
{make_tag("rect", x=0, y=offset, width=char_width * width, height=line_height + 0.25)}
        </clipPath>"""          # noqa E501
        for line_no, offset in enumerate(line_offsets)
    )

    styles = "\n".join(
        f".{unique_id}-r{rule_no} {{ {css} }}" for css, rule_no in classes.items()  # noqa E501
    )
    backgrounds = "".join(text_backgrounds)
    matrix = "".join(text_group)

    terminal_width = ceil(width * char_width + padding_width)
    terminal_height = (y + 1) * line_height + padding_height
    chrome = make_tag(
        "rect",
        fill=_theme.background_color.hex,
        stroke="rgba(255,255,255,0.35)",
        stroke_width="1",
        x=margin_left,
        y=margin_top,
        width=terminal_width,
        height=terminal_height,
        rx=8,
    )

    title_color = _theme.foreground_color.hex
    if title:
        chrome += make_tag(
            "text",
            escape_text(title),
            _class=f"{unique_id}-title",
            fill=title_color,
            text_anchor="middle",
            x=terminal_width // 2,
            y=margin_top + char_height + 6,
        )
    chrome += """
        <g transform="translate(26,22)">
        <circle cx="0" cy="0" r="7" fill="#ff5f57"/>
        <circle cx="22" cy="0" r="7" fill="#febc2e"/>
        <circle cx="44" cy="0" r="7" fill="#28c840"/>
        </g>
    """

    svg = code_format.format(
        unique_id=unique_id,
        char_width=char_width,
        char_height=char_height,
        line_height=line_height,
        terminal_width=char_width * width - 1,
        terminal_height=(y + 1) * line_height - 1,
        width=terminal_width + margin_width,
        height=terminal_height + margin_height,
        terminal_x=margin_left + padding_left,
        terminal_y=margin_top + padding_top,
        styles=styles,
        chrome=chrome,
        backgrounds=backgrounds,
        matrix=matrix,
        lines=lines,
    )
    return svg


Console.export_svg = export_svg

# # Mkdocs material colors
# # Defaults
#   --md-default-fg-color:           hsla(0, 0%, 0%, 0.87);
#                                    rgba(0, 0, 0, 0.87)
#   --md-default-fg-color--light:    hsla(0, 0%, 0%, 0.54);
#                                    rgba(0, 0, 0, 0.54)
#   --md-default-fg-color--lighter:  hsla(0, 0%, 0%, 0.32);
#                                    rgba(0, 0, 0, 0.32)
#   --md-default-fg-color--lightest: hsla(0, 0%, 0%, 0.07);
#                                    rgba(0, 0, 0, 0.07)
#   --md-default-bg-color:           hsla(0, 0%, 100%, 1);
#                                    rgba(255, 255, 255, 1)
#   --md-default-bg-color--light:    hsla(0, 0%, 100%, 0.7);
#                                    rgba(255, 255, 255, 0.7)
#   --md-default-bg-color--lighter:  hsla(0, 0%, 100%, 0.3);
#                                    rgba(255, 255, 255, 0.3)
#   --md-default-bg-color--lightest: hsla(0, 0%, 100%, 0.12);
#                                    rgba(255, 255, 255, 0.12)

# # code

#   --md-code-fg-color:          hsla(200, 18%, 26%, 1);
#                                rgba(54, 70, 78, 1)
#   --md-code-bg-color:          hsla(0, 0%, 96%, 1);
#                                rgba(244, 244, 244, 1)

#   // Code highlighting color shades
#   --md-code-hl-color:          hsla(#{hex2hsl($clr-yellow-a200)}, 0.5);
#                                rgba(254, 255, 0, 0.5)
#   --md-code-hl-number-color:   hsla(0, 67%, 50%, 1);
#                                rgba(212, 42, 42, 1)
#   --md-code-hl-special-color:  hsla(340, 83%, 47%, 1);
#                                rgba(219, 20, 86, 1)
#   --md-code-hl-function-color: hsla(291, 45%, 50%, 1);
#                                rgba(167, 70, 184, 1)
#   --md-code-hl-constant-color: hsla(250, 63%, 60%, 1);
#                                rgba(110, 88, 217, 1)
#   --md-code-hl-keyword-color:  hsla(219, 54%, 51%, 1);
#                                rgba(62, 109, 197, 1)
#   --md-code-hl-string-color:   hsla(150, 63%, 30%, 1);
#                                rgba(28, 124, 76, 1)
#   --md-code-hl-name-color:        var(--md-code-fg-color);
#   --md-code-hl-operator-color:    var(--md-default-fg-color--light);
#   --md-code-hl-punctuation-color: var(--md-default-fg-color--light);
#   --md-code-hl-comment-color:     var(--md-default-fg-color--light);
#   --md-code-hl-generic-color:     var(--md-default-fg-color--light);
#   --md-code-hl-variable-color:    var(--md-default-fg-color--light);

# Color picker based from dark mode setting:
# --md-code-hl-number-color            rgb(215, 112, 97)
# --md-code-hl-special-color           rgb(223, 105, 144)
# --md-code-hl-function-color          rgb(189, 122, 211)
# --md-code-hl-constant-color          rgb(144, 134, 220)
# --md-code-hl-keyword-color           rgb(111, 146, 218)
# --md-code-hl-string-color            rgb(90, 174, 118)
# --md-code-hl-name-color              rgb(213, 215, 225)
# --md-code-hl-operator-color          rgb(148, 152, 175)
# --md-code-hl-punctuation-color       rgb(148, 152, 175)
# --md-code-hl-comment-color           rgb(148, 152, 175)
# --md-code-hl-generic-color           rgb(148, 152, 175)
# --md-code-hl-variable-color          rgb(148, 152, 175)

# Code block foreground, background and line highlight colors are defined via:

# --md-code-fg-color                   rgb(213, 215, 225)
# --md-code-bg-color                   rgb(33, 34, 43)
# --md-code-hl-color                   rgb(51, 61, 89)

# Mkdocs material terminal theme
MATERIAL_DARK = TerminalTheme(
    parse_rgb_hex('263238'),            # background
    parse_rgb_hex('ECEFF1'),            # foreground
    # Normal colorset
    [parse_rgb_hex('546E7A'),           # black
     parse_rgb_hex('FF5252'),           # red
     parse_rgb_hex('5CF19E'),           # green
     parse_rgb_hex('FFD740'),           # yellow
     parse_rgb_hex('40C4FF'),           # blue
     parse_rgb_hex('FF4081'),           # magenta
     parse_rgb_hex('64FCDA'),           # cyan
     parse_rgb_hex('FFFFFF')],          # white
    # Bright colorset
    [parse_rgb_hex('B0BEC5'),           # black
     parse_rgb_hex('FF8A80'),           # red
     parse_rgb_hex('B9F6CA'),           # green
     parse_rgb_hex('FFE57F'),           # yellow
     parse_rgb_hex('80D8FF'),           # blue
     parse_rgb_hex('FF80AB'),           # magenta
     parse_rgb_hex('A7FDEB'),           # cyan
     parse_rgb_hex('FFFFFF')],          # white
)

MATERIAL_DARK_2 = TerminalTheme(
    (33, 34, 43),            # background
    (213, 215, 225),         # foreground
    # parse_rgb_hex('263238'),            # background
    # parse_rgb_hex('ECEFF1'),            # foreground
    # Normal colorset
    [parse_rgb_hex('546E7A'),           # black
     parse_rgb_hex('FF5252'),           # red
     (28, 124, 76),       # parse_rgb_hex('5CF19E'),  # green
     parse_rgb_hex('FFD740'),           # yellow
     parse_rgb_hex('40C4FF'),           # blue
     parse_rgb_hex('FF4081'),           # magenta
     parse_rgb_hex('64FCDA'),           # cyan
     parse_rgb_hex('FFFFFF')],          # white
    # Bright colorset
    [parse_rgb_hex('B0BEC5'),           # black
     parse_rgb_hex('FF8A80'),           # red
     parse_rgb_hex('B9F6CA'),           # green
     parse_rgb_hex('FFE57F'),           # yellow
     parse_rgb_hex('80D8FF'),           # blue
     parse_rgb_hex('FF80AB'),           # magenta
     parse_rgb_hex('A7FDEB'),           # cyan
     parse_rgb_hex('FFFFFF')],          # white
)

MKDOCS_MATERIAL_DARK = TerminalTheme(
    (33, 34, 43),            # background
    (213, 215, 225),         # foreground
    # Normal colorset
    [parse_rgb_hex('546E7A'),           # black
     (215, 112, 97),      # parse_rgb_hex('FF5252'),  # red
     (28, 124, 76),       # parse_rgb_hex('5CF19E'),  # green
     (144, 134, 220),  # parse_rgb_hex('FFD740'),     # yellow
     (111, 146, 218),  # parse_rgb_hex('40C4FF'),     # blue
     (223, 105, 144),  # parse_rgb_hex('FF4081'),     # magenta
     (90, 174, 118),   # parse_rgb_hex('64FCDA'),     # cyan
     parse_rgb_hex('FFFFFF')],          # white
    # Bright colorset
    [parse_rgb_hex('B0BEC5'),           # black
     parse_rgb_hex('FF8A80'),           # red
     parse_rgb_hex('B9F6CA'),           # green
     parse_rgb_hex('FFE57F'),           # yellow
     parse_rgb_hex('82B1FF'),  # parse_rgb_hex('80D8FF'),  # blue
     parse_rgb_hex('FF80AB'),           # magenta
     parse_rgb_hex('00BCD4'),  # parse_rgb_hex('A7FDEB'),  # cyan
     parse_rgb_hex('FFFFFF')],          # white
)


def walk_directory(directory: pathlib.Path,
                   tree: Tree,
                   ext_filt=None,
                   path_filt=None) -> None:
    """Recursively build a Tree with directory contents."""
    if path_filt and not isinstance(path_filt, list):
        raise TypeError("path_filt must be a list")

    else:
        path_filt = []

    if ext_filt and not isinstance(ext_filt, list):
        raise TypeError("ext_filt must be a list")
    elif ext_filt:
        new_ext_filt = []
        for ext in ext_filt:
            if not ext.startswith("."):
                ext = "." + ext
            new_ext_filt.append(ext)

        ext_filt = new_ext_filt
    else:
        ext_filt = []

    # Sort dirs first then by filename
    paths = sorted(
        pathlib.Path(directory).iterdir(),
        key=lambda path: (path.is_file(), path.name.lower()),
    )
    for path in paths:

        if path.suffix and path.suffix is not None:
            if path.suffix in ext_filt:
                continue

        if any([pfilt in path for pfilt in path_filt]):
            continue

        # Remove hidden files
        if path.name.startswith("."):
            continue
        if path.is_dir():
            style = "dim" if path.name.startswith("__") else ""

            branch = tree.add(
                "[bold magenta]:open_file_folder: " +
                f"[link file://{path}]{escape(path.name)}",
                style=style,
                guide_style=style,
            )
            walk_directory(path,
                           branch,
                           path_filt=path_filt,
                           ext_filt=ext_filt)
        else:
            text_filename = Text(path.name, "green")
            text_filename.highlight_regex(r"\..*$", "bold red")
            text_filename.stylize(f"link file://{path}")
            file_size = path.stat().st_size
            text_filename.append(f" ({decimal(file_size)})", "blue")
            icon = "🐍 " if path.suffix == ".py" else "📄 "
            tree.add(Text(icon) + text_filename)


def setup_argparse():
    parser = argparse.ArgumentParser(
        description='Render tree view of specified directories.'
    )

    parser.add_argument('path',
                        help="Path to directory to render")

    parser.add_argument('-t', '--title', default='',
                        help="Optional title for svg image.")

    parser.add_argument('-o', '--obfuscate_path',
                        help="Optional path obfuscation to hide user " +
                        "system details.")

    parser.add_argument('-s', '--save-name',
                        help="Optional name for svg output." +
                        " Defaults to last dir in path.")

    parser.add_argument('-f', '--filter-paths',
                        help="List of paths to exlude")

    parser.add_argument('-e', '--ext-filter', nargs='+', default=['svg'],
                        help="File extensions to exclude")

    args = parser.parse_args()
    return args


def main(args):

    if not args.path:
        return -1

    directory = os.path.abspath(args.path)
    if not pathlib.Path(directory).is_dir():
        print("path must be a directory, not a file")
        return -1

    if not args.save_name:
        args.save_name = pathlib.Path(directory).parts[-1] + '.svg'
    elif not args.save_name.endswith('.svg'):
        args.save_name += ".svg"

    if not args.obfuscate_path:
        obfuscate_path = "/path/to/maestro/study/output/"
        pathname = pathlib.PurePath(obfuscate_path,
                                    pathlib.Path(directory).parts[-1])

    else:
        pathname = directory

    tree = Tree(
        f":open_file_folder: [link file://{pathname}]{pathname}",
        guide_style="bold bright_blue",
    )
    walk_directory(pathlib.Path(directory),
                   tree,
                   ext_filt=args.ext_filter,
                   path_filt=args.filter_paths)

    console = Console(record=True)
    console.print(tree)
    console.save_svg(args.save_name,
                     title=args.title,
                     theme=MATERIAL_DARK_2)


if __name__ == "__main__":
    args = setup_argparse()

    sys.exit(main(args))
