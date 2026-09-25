; Syntax highlighting for BrightScript (workload W11, docs/validation/workload-matrix.md).
; Capture names are those of the Tree-sitter CLI default theme.

; Comments and inactive conditional-compilation text
(comment) @comment
(inactive_text) @comment

; Literals
(string) @string
(error_message) @string.special
(number) @number
[
  (true)
  (false)
  (invalid)
  (source_literal)
] @constant.builtin

; Types
(type) @type.builtin

; Identifiers. tree-sitter-highlight (crates/highlight @ v0.27.0) keeps the
; last pattern that captures a node, so the generic `@variable` comes first
; and each more specific role follows it.
(identifier) @variable

; `m` (BS-FUNC-013)
((identifier) @variable.builtin
  (#match? @variable.builtin "^[mM]$"))

; Members, keys and XML attributes
; A member property is the identifier right after `.` or `?.`; matching the
; sibling pair, not the parent, keeps left-deep chains linear (S07-M03).
(["." "?."] . (identifier) @property)

(associative_array_entry
  key: (identifier) @property)

; Likewise the identifier right after `@` or `?@`.
(["@" "?@"] . (identifier) @attribute)

; Functions
(function_declaration
  name: (identifier) @function)

(call_expression
  function: (identifier) @function)

(call_expression
  function: (member_expression
    property: (identifier) @function))

; Calls of reserved callable names, in any letter case (BS-LEX-022)
(call_expression
  function: (identifier) @function.builtin
  (#match? @function.builtin "^([bB][oO][xX]|[cC][rR][eE][aA][tT][eE][oO][bB][jJ][eE][cC][tT]|[eE][vV][aA][lL]|[gG][eE][tT][gG][lL][oO][bB][aA][lL][aA][aA]|[gG][eE][tT][lL][aA][sS][tT][rR][uU][nN][cC][oO][mM][pP][iI][lL][eE][eE][rR][rR][oO][rR]|[gG][eE][tT][lL][aA][sS][tT][rR][uU][nN][rR][uU][nN][tT][iI][mM][eE][eE][rR][rR][oO][rR]|[pP][oO][sS]|[rR][uU][nN]|[tT][aA][bB]|[tT][yY][pP][eE])$"))

(parameter
  name: (identifier) @variable.parameter)

; Labels and conditional-compilation constants
(label_statement
  name: (identifier) @constant)

(goto_statement
  label: (identifier) @constant)

(const_directive
  name: (identifier) @constant)

(const_directive
  value: (identifier) @constant)

(if_directive
  condition: (identifier) @constant)

(else_if_directive
  condition: (identifier) @constant)

; Keywords. `function` and `sub` are keywords only in declarations; as a
; return or parameter type `function` is part of `type`.
(function_declaration
  [
    "function"
    "sub"
  ] @keyword)

(anonymous_function
  [
    "function"
    "sub"
  ] @keyword)

[
  "if"
  "then"
  "else"
  "elseif"
  "end"
  "endif"
  "for"
  "each"
  "in"
  "to"
  "step"
  "next"
  "while"
  "endwhile"
  "exit"
  "exitwhile"
  "continue"
  "return"
  "print"
  "?"
  "dim"
  "goto"
  "stop"
  "library"
  "try"
  "catch"
  "endtry"
  "throw"
  "endfunction"
  "endsub"
  "as"
  "end if"
  "end for"
  "end while"
  "end sub"
  "end function"
  "end try"
  "#const"
  "#if"
  "#else"
  "#end"
  "#error"
] @keyword

; Operators, including the word operators and optional chaining
[
  "="
  "+="
  "-="
  "*="
  "/="
  "\\="
  "<<="
  ">>="
  "++"
  "--"
  "^"
  "*"
  "/"
  "\\"
  "mod"
  "+"
  "-"
  "<<"
  ">>"
  "<>"
  "<"
  ">"
  "<="
  ">="
  "not"
  "and"
  "or"
  "@"
  "?."
  "?@"
  "?["
  "?("
] @operator

; Punctuation
[
  "("
  ")"
  "["
  "]"
  "{"
  "}"
] @punctuation.bracket

[
  ","
  ";"
  ":"
  "."
] @punctuation.delimiter
