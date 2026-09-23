' Anonymous tokens carrying requirements of the (token) catalogue fixtures.
x = array?[3]?.foo?.bar?()
'        ^ operator
'            ^ operator
'                 ^ operator
'                      ^ operator
x = i?(1, "String", explode())
'    ^ operator
y = i?[explode()]
'    ^ operator
a = b ?. c
'     ^ operator
x = s ?[ 5 ]
'     ^ operator
y = f ?( 1 )
'     ^ operator
z = e ?@ id
'     ^ operator
x = a?.b.c?[0]?(1)
'    ^ operator
'         ^ operator
'             ^ operator
y = f(1)[2].g(3)
IF x?("Hello")
' <- keyword
'   ^ operator
  PRINT "Hi"
' ^ keyword
END IF
' <- keyword
?("Hello")
' <- keyword
?.1
' <- keyword
'^ number
?[1]
' <- keyword
