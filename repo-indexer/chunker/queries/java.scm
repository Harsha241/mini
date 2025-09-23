; ======================
; Java Tree-sitter Query for Chunking
; ======================

; ======================
; Imports & Packages
; ======================
(package_declaration
  name: (scoped_identifier) @package.name) @package.node

(import_declaration
  (scoped_identifier) @import.name) @import.node

; ======================
; Classes & Inheritance
; ======================
(class_declaration
  name: (identifier) @class.name
  superclasses: (superclass (type_identifier) @class.extends)?
  interfaces: (super_interfaces (type_identifier) @class.implements)?
  body: (class_body) @class.body) @class.node

; ======================
; Interfaces
; ======================
(interface_declaration
  name: (identifier) @interface.name
  body: (interface_body) @interface.body) @interface.node

; ======================
; Methods
; ======================
(method_declaration
  name: (identifier) @method.name
  body: (block) @method.body) @method.node

; ======================
; Constructors
; ======================
(constructor_declaration
  name: (identifier) @constructor.name
  body: (block) @constructor.body) @constructor.node

; ======================
; Fields
; ======================
(field_declaration
  declarator: (variable_declarator
    name: (identifier) @field.name)) @field.node

; ======================
; Comments
; ======================
(line_comment) @comment.node
(block_comment) @comment.node

; ======================
; Top-level statements
; ======================
(expression_statement) @statement.node
(local_variable_declaration) @statement.node
(if_statement) @statement.node
(for_statement) @statement.node
(while_statement) @statement.node
(try_statement) @statement.node

; ======================
; Method calls
; ======================
(method_invocation
  name: (identifier) @call.method) @call.node

(object_creation_expression
  type: (type_identifier) @call.constructor) @call.node

; ======================
; Module-level blocks
; ======================
(program) @module.node

