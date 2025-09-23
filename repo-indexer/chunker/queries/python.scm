; ======================
; Python Tree-sitter Query for Chunking
; ======================

; ======================
; Imports
; ======================
(import_statement
  name: (dotted_name) @import.name) @import.node

(import_from_statement
  module_name: (dotted_name) @from.module
  name: (dotted_name) @imported.symbol) @import.node

; ======================
; Classes
; ======================
(class_definition
  name: (identifier) @class.name
  bases: (argument_list (identifier) @class.base)?
  body: (block) @class.body) @class.node

; ======================
; Functions
; ======================
(function_definition
  name: (identifier) @function.name
  body: (block) @function.body) @function.node

; ======================
; Async Functions
; ======================
(async_function_definition
  name: (identifier) @function.name
  body: (block) @function.body) @function.node

; ======================
; Methods (inside classes)
; ======================
(class_definition
  body: (block
    (function_definition
      name: (identifier) @method.name
      body: (block) @method.body) @method.node))

; ======================
; Docstrings & Comments
; ======================
(expression_statement (string) @docstring) @docstring.node
(comment) @comment.node

; ======================
; Top-level statements
; ======================
(expression_statement) @statement.node
(assignment) @statement.node
(if_statement) @statement.node
(for_statement) @statement.node
(while_statement) @statement.node
(try_statement) @statement.node
(with_statement) @statement.node

; ======================
; Module-level blocks
; ======================
(module) @module.node

