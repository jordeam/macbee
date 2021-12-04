function led_check(elt) {
    if (elt.checked)
        r = httpGet('/set_led/' + elt.id +'/1');
    else
        r = httpGet('/set_led/' + elt.id +'/0');
    if (r == "0")
        elt.checked = false;
    else
        elt.checked = true;
}

function httpGet(theUrl) {
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "GET", theUrl, false ); // false for synchronous request
    xmlHttp.send( null );
    return xmlHttp.responseText;
}

function led_init_check(led) {
    r = httpGet("/get_led/" + led);
    if (r == "0")
        document.getElementById(led).checked = false;
    else
        document.getElementById(led).checked = true;
}

window.onload = function() {
    // led_init_check("led1");
    // led_init_check("led2");
    // led_init_check("led3");
    // led_init_check("led4");
}
