; ======================
; Imports & Packages
; ======================
(package_declaration
  name: (scoped_identifier) @package.name)

(import_declaration
  (scoped_identifier) @import.name)

; ======================
; Classes & Inheritance
; ======================
(class_declaration
  name: (identifier) @class.name
  superclasses: (superclass (type_identifier) @class.extends)?
  interfaces: (super_interfaces (type_identifier) @class.implements)?
  body: (class_body
          (method_declaration
             name: (identifier) @method.name)
          (class_declaration
             name: (identifier) @inner.class.name))) ; nested class

; ======================
; Interfaces
; ======================
(interface_declaration
  name: (identifier) @interface.name
  body: (interface_body
          (method_declaration
             name: (identifier) @method.name)))

; ======================
; Comments
; ======================
(comment) @comment
; ======================
; Method Calls
; ======================
(method_invocation
  name: (identifier) @call.method)

(object_creation_expression
  type: (type_identifier) @call.constructor)
