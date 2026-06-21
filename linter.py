from re import Match, Pattern
from typing import Iterable

from SublimeLinter.lint.base_linter.php_linter import PhpLinter
from SublimeLinter.lint.linter import LintMatch
from sublime import FindFlags

SELECTOR = "embedding.php"
REPORTING_FORMAT = "github"


class Mago(PhpLinter):
    cmd: str = f'mago analyze --reporting-format {REPORTING_FORMAT} "$file"'
    defaults: "dict[str, str | bool]" = {"selector": SELECTOR, "disable": True}
    error_types: str = "note|notice|help|warning|error"

    regex_short: str = (
        r"^(?P<filename>.+?):"
        r"(?P<line>\d+):"
        r"(?P<col>\d+): "
        rf"(?P<error_type>{error_types})"
        r"\[(?P<code>.+?)\]: "
        r"(?P<message>.+)"
    )

    regex_medium: str = (
        r"^(?P<filename>.+?):"
        r"(?P<line>\d+):"
        r"(?P<col>\d+): "
        rf"(?P<error_type>{error_types})"
        r"\[(?P<code>.+?)\]: "
        r"(?P<message>.+(\s+=\s+.+)+)"
    )

    regex_github: str = (
        rf"^::(?P<error_type>{error_types}) "
        r"file=(?P<filename>.+?),"
        r"line=(?P<line>\d+),"
        r"endLine=(?P<end_line>\d+),"
        r"col=(?P<col>\d+),"
        r"endColumn=(?P<end_col>\d+),"
        r"title=(?P<code>.+?)::"
        r"(?P<message>.+)"
    )

    regex: "None | str | Pattern[str]" = regex_github
    multiline: bool = True

    def split_match(self, match: "Match[str]") -> LintMatch:
        error = super().split_match(match)

        error.message = error.message.replace("%0A%0AHelp", "\n­\n💡 Help")
        error.message = error.message.replace("%0A>", "\n👉 ")
        error.message = error.message.replace("%0A%0A", "\n­\n➖ ")
        error.message = error.message.replace("%0A", "\n➖ ")

        return error


class MagoAnalyze(Mago):
    defaults: "dict[str, str | bool]" = {"selector": SELECTOR, "disable": False}

    name: str = "mago-analyze"


class MagoLint(Mago):
    name: str = "mago-lint"

    defaults: "dict[str, str | bool]" = {"selector": SELECTOR, "disable": False}
    cmd: str = f'mago lint --reporting-format {REPORTING_FORMAT} "$file"'


class MagoGuard(Mago):
    name: str = "mago-guard"

    defaults: "dict[str, str | bool]" = {"selector": SELECTOR, "disable": False}
    cmd: str = f'mago guard --reporting-format {REPORTING_FORMAT} "$file"'


class MagoFormat(Mago):
    name: str = "mago-format"

    defaults: "dict[str, str | bool]" = {"selector": SELECTOR, "disable": False}
    cmd: str = 'mago format --dry-run "$file"'

    regex: "None | str | Pattern[str]" = None

    def find_errors(self, output: str) -> Iterable[LintMatch]:
        output_lines: list[str] = []
        lint_matches: Iterable[LintMatch] = []

        for output_line in output.splitlines():
            if (
                not output_line.startswith('-')
                and not output_line.startswith('+')
            ):
                continue

            if (
                output_line.startswith('---')
                or output_line.startswith('+++')
            ):
                continue

            output_lines.append(output_line)

        index = 0

        while index < len(output_lines):
            filtered_output_line = output_lines[index]

            if filtered_output_line.startswith('-'):
                region = self.view.find(
                    filtered_output_line[1:],
                    0,
                    FindFlags.LITERAL,
                )

                line = self.view.rowcol(region.a)[0]
                message = ''
                next_index = index + 1

                while next_index < len(output_lines):
                    next_filtered_output_line = output_lines[next_index]

                    if not next_filtered_output_line.startswith('+'):
                        break

                    if not message:
                        message += '­\n'

                    message += next_filtered_output_line[1:] + '\n'
                    next_index += 1

                lint_matches.append(LintMatch({
                    'line': line,
                    'end_line': line,
                    'message': message,
                }))

            index += 1

        return lint_matches
