' W03 compact sample: one-line bodies, compact terminators, case variants.
FUNCTION Double(v AS INTEGER) AS INTEGER : v = v * 2 : RETURN v : ENDFUNCTION
Sub Tick(n As Integer) : n++ : ? n : EndSub

function Classify(score as integer) as string
    If score >= 90 Then
        grade = "A"
    ElseIf score >= 80 THEN
        grade = "B"
    elseif score >= 70
        grade = "C"
    Else
        grade = "F"
    EndIf
    Return grade
EndFunction

sub Drain(queue as object)
    WHILE queue.Count() > 0
        item = queue.Pop()
        if item = invalid then ExitWhile
        ?item
    EndWhile
    while true : exitwhile : endwhile
    For Each entry In queue : ? entry : End For
    for i = 1 to 3 : print i; : next
    Try : Risky() : Catch problem : ?"failed: "; problem : EndTry
    ?("parenthesized")
    ?.5
    ?[1, 2]
    ? : print
end sub
