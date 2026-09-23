' W03 composite sample: independently written, exercises every documented form.
Library "v30/bslCore.brs"

#const traceEnabled = true
#const verboseTrace = traceEnabled

REM ---------------------------------------------------------------- entry point
sub Main(args as Object, retries = 3 as Integer)
    settings = LoadSettings("app")
    counter = 0
    counter++
    counter--
    counter += 10
    counter -= 2
    counter *= 3
    counter /= 2
    counter \= 2
    counter <<= 1
    counter >>= 1
    settings.title = "Inventory"
    settings.limits[0] = 5
    settings.limits[1, 2] = 7
    settings.items.push("first")
    Report(settings, counter)

#if traceEnabled
    print "trace on"
#else if verboseTrace
    print "verbose only"
#else
    #error trace flags missing
#end if

    if retries > 0 and not settings.disabled then print "retrying" else print "done"
    if counter = 0 then counter = 1 : print counter
    if args <> invalid then
        print "has arguments"
    else if retries = 0 then
        print "no retries"
    else
        print "defaults"
    end if

    dim grid[3, 4]
    dim cube(2, 2, 2)
    for row = 0 to 3 step 1
        for col = 3 to 0 step -1
            if col = row then continue for
            grid[row, col] = row * col
        end for
    next
    for each key in settings
        if key = "stop" then exit for
        print key; " = "; settings[key]
    end for
    pending = 3
    while pending > 0
        pending--
        if pending = 1 then continue while
        if pending = 0 then exit while
    end while

retry:
    attempt = Attempt(retries)
    if attempt = invalid then goto retry
    print "zones", "a"; "b" tab(20) "column" pos(0)
    print "total: " counter "!"
    ? LINE_NUM
    stop
    end
end sub

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
            throw { message: "nested", code: 42 }
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
