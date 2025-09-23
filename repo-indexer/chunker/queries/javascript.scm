; ======================
; JavaScript/TypeScript Tree-sitter Query for Chunking
; ======================

; ======================
; Imports
; ======================
(import_statement
  source: (string) @import.source) @import.node

(import_declaration
  source: (string) @import.source) @import.node

; ======================
; Classes
; ======================
(class_declaration
  name: (identifier) @class.name
  body: (class_body) @class.body) @class.node

; ======================
; Functions
; ======================
(function_declaration
  name: (identifier) @function.name
  body: (block_statement) @function.body) @function.node

(function_expression
  name: (identifier) @function.name
  body: (block_statement) @function.body) @function.node

; ======================
; Arrow Functions
; ======================
(arrow_function
  body: (block_statement) @function.body) @function.node

; ======================
; Methods (inside classes)
; ======================
(class_declaration
  body: (class_body
    (method_definition
      name: (property_identifier) @method.name
      body: (block_statement) @method.body) @method.node))

; ======================
; Object Methods
; ======================
(object
  (pair
    key: (property_identifier) @method.name
    value: (function_expression
      body: (block_statement) @method.body) @method.node))

; ======================
; Comments
; ======================
(comment) @comment.node

; ======================
; Top-level statements
; ======================
(expression_statement) @statement.node
(variable_declaration) @statement.node
(if_statement) @statement.node
(for_statement) @statement.node
(while_statement) @statement.node
(try_statement) @statement.node

; ======================
; Module-level blocks
; ======================
(program) @module.node

