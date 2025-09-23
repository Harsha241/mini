; ======================
; Imports
; ======================
(import_statement
  name: (dotted_name) @import.name)

(import_from_statement
  module_name: (dotted_name) @from.module
  name: (dotted_name) @imported.symbol)

; ======================
; Classes
; ======================
(class_definition
  name: (identifier) @class.name
  bases: (argument_list (identifier) @class.base)?
  body: (block
          (function_definition
             name: (identifier) @method.name)
          (class_definition
             name: (identifier) @inner.class.name))) ; nested class

; ======================
; Functions
; ======================
(function_definition
  name: (identifier) @function.name)

; ======================
; Docstrings & Comments
; ======================
(expression_statement (string) @docstring) ; top-level or function/class docstring
(comment) @comment
; ======================
; Function Calls
; ======================
(call
  function: (identifier) @call.func)

(call
  function: (attribute
              object: (identifier) @call.object
              attribute: (identifier) @call.method))
