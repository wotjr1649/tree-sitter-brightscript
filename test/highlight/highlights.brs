' Highlight assertions for every W11 capture row.
Library "v30/bslCore.brs"
' <- keyword
'       ^ string
#const Debug = true
' <- keyword
'      ^ constant
'            ^ operator
'              ^ constant.builtin
#const Trace = Debug
'              ^ constant
#if Debug
' <- keyword
'   ^ constant
    #error not ready yet
'   ^ keyword
'          ^ string.special
#else if Trace
' <- keyword
'     ^ keyword
'        ^ constant
#else
' <- keyword
#end if
' <- keyword
'    ^ keyword
#if false
'   ^ constant.builtin
    prose inside a false branch
'   ^ comment
#end if
function Compute(count as Integer, label = invalid as String) as Object
' <- keyword
'        ^ function
'               ^ punctuation.bracket
'                ^ variable.parameter
'                      ^ keyword
'                         ^ type.builtin
'                                ^ punctuation.delimiter
'                                  ^ variable.parameter
'                                          ^ constant.builtin
'                                                     ^ type.builtin
'                                                                ^ type.builtin
    total = count * 2 + 1.5 mod 3 ' trailing note
'   ^ variable
'           ^ variable
'                 ^ operator
'                   ^ number
'                     ^ operator
'                       ^ number
'                           ^ operator
'                                 ^ comment
    m.total = total
'   ^ variable.builtin
'    ^ punctuation.delimiter
'     ^ property
    node = CreateObject("roXMLElement")
'          ^ function.builtin
    kind = TYPE(node)
'          ^ function.builtin
    title = node@title
'               ^ operator
'                ^ attribute
    node.load(label)
'        ^ function
    helper(total)
'   ^ function
    info = { name: label, "key": LINE_NUM }
'          ^ punctuation.bracket
'            ^ property
'                ^ punctuation.delimiter
'                         ^ string
'                                ^ constant.builtin
    list = [1, 2]
'          ^ punctuation.bracket
'               ^ punctuation.bracket
    if not total >= 3 and count <> 0 or false then print total; "x" else ? total
'   ^ keyword
'      ^ operator
'                ^ operator
'                     ^ operator
'                               ^ operator
'                                    ^ operator
'                                             ^ keyword
'                                                  ^ keyword
'                                                             ^ punctuation.delimiter
'                                                                   ^ keyword
'                                                                        ^ keyword
    for i = 1 to 10 step 2
'   ^ keyword
'             ^ keyword
'                   ^ keyword
        if i = 5 then exit for
'                     ^ keyword
'                          ^ keyword
        if i = 7 then continue for
'                     ^ keyword
    next
'   ^ keyword
    for each item in list : total += item : end for
'       ^ keyword
'                 ^ keyword
'                                 ^ operator
'                                           ^ keyword
    while total > 0 : total-- : end while
'   ^ keyword
'                          ^ operator
'                               ^ keyword
    dim grid[2, 2]
'   ^ keyword
again:
' <- constant
    try
'   ^ keyword
        throw "failed"
'       ^ keyword
    catch problem
'   ^ keyword
'         ^ variable
        goto again
'       ^ keyword
'            ^ constant
    end try
'   ^ keyword
    callback = sub(x) : stop : end sub
'              ^ keyword
'                       ^ keyword
'                              ^ keyword
    return total
'   ^ keyword
end function
' <- keyword
sub Tail() : end : endsub
'            ^ keyword
'                  ^ keyword
sub Register(handler as Function)
'            ^ variable.parameter
'                       ^ type.builtin
end sub
' <- keyword
