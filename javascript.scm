; ======================
; Imports
; ======================
(import_declaration
    (scoped_identifier) @import.name)

; ======================
; Classes
; ======================
(class_declaration
    name: (identifier) @class.name
    body: (class_body) @class.body)

; ======================
; Methods
; ======================
(method_declaration
    name: (identifier) @method.name
    body: (block) @method.body)
    




; ======================
; Variables
; ======================
(variable_declarator
    name: (identifier) @var.name
    value: (_) @var.value)

; ======================
; Object creation (constructor calls)
; ======================
(object_creation_expression
    type: (type_identifier) @call.constructor
    arguments: (argument_list) @call.arguments)

; ======================
; Method calls
; ======================
(method_invocation
    object: (_) @call.object
    name: (identifier) @call.method
    arguments: (argument_list) @call.arguments)

(method_invocation
    name: (identifier) @call.method
    arguments: (argument_list) @call.arguments)

; ======================
; Unified call expressions
; ======================
(object_creation_expression) @call.expression
(method_invocation) @call.expression

; ======================
; Comments
; ======================
(line_comment) @comment
(block_comment) @comment

