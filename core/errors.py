
class ErrorCollector:

    def __init__(self):
        self.issues = []

    def add(self, issue):
        self.issues.append(issue)
        self.issues.sort()

    def ok(self):
        return not any(not issue.warning for issue in self.issues)

    def show(self):
        for issue in self.issues:
            print(issue)

    def clear(self):
        self.issues = []


class Position:

    def __init__(self, file, line, col, full_line):
        self.file = file
        self.line = line
        self.col = col
        self.full_line = full_line

    def __add__(self, other):
        return Position(self.file, self.line, self.col + 1, self.full_line)



error_collector = ErrorCollector()

class Range:

    def __init__(self, start, end=None):
        self.start = start
        self.end = end or start

    def __add__(self, other):
        return Range(self.start, other.end)


class CompilerError(Exception):

    def __init__(self, descrip, range=None, warning=False):
        self.descrip = descrip
        self.range = range
        self.warning = warning

    def __str__(self):
        error_color = "\x1B[31m"
        warn_color = "\x1B[33m"
        reset_color = "\x1B[0m"

        color_code = warn_color if self.warning else error_color
        issue_type = "warning" if self.warning else "error"

        return (f"{color_code}{issue_type}:{reset_color} {self.descrip}")


    def __lt__(self, other):

        if not self.range:
            return bool(other.range)

        if self.range.start.file != other.range.start.file:
            return False

        this_tuple = self.range.start.line, self.range.start.col
        other_tuple = other.range.start.line, other.range.start.col
        return this_tuple < other_tuple
