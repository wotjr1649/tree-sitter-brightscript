
function LoadSettings(name as String, fallback = invalid as Dynamic) as Object
    values = [
        1       ' first value
        2,
        &hFF, &h1f&, 9876543210&
        3.5, 1.5e3, 2.5d-2, .25, 7!, 8#, 9%
    ]
    table = {
        title: name,
        "quoted key": true
        values: values ' trailing comment
        flag: false,
    }
    table.onLoad = function(event as Object) as Boolean
        return event?.data?["ok"] = true
    end function
    table.onClose = sub()
        print "closed"
    end sub
    return table
end function

sub Report(data as Object, total as Float)
    xmlNode = data.xml
    title = xmlNode@title
    maybe = data?.nested?.child?@attr
    callback = data.handler?(1, "two")
    result = -2 ^ 2 + 3 * 4 / 2 mod 5 \ 2 - (1 + 2) << 1 >> 1
    compare = result = 3 or result <> 4 and result < 5 or result > 6 and result <= 7 and result >= 8
    negated = not compare
    text = "say ""hello""" + 5.tostr() + "x".left(1)
    print title; maybe; callback; result; compare; negated; text
end sub

function Attempt(times as Integer) as Dynamic
    try
        if times < 0 then throw "negative"
        try
            inner = CreateObject("roAssociativeArray")
            throw { message: "nested", code: 42 
        catch innerError
            print innerError.message
            throw innerError
        end try
    catch outerError
        print "caught: "; outerError
        return invalid
    end try
    return times
end function
