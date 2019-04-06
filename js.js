PORT = 8000

function get(pathname) {
    const Http = new XMLHttpRequest();
    const url = window.location.protocol + '//' + window.location.hostname + ':' + PORT + pathname
    Http.open("GET", url);
    Http.send();
}

function handleForm() {
    const alt = document.getElementById('latitude').value;
    const long = document.getElementById('longitude').value;
    const sat_id = document.getElementById('sat_id').value;

    const pathname = "/track/" + alt + "/" + long + "/" + sat_id
    get(pathname)

//    window.location = "/" + alt + "/" + long + "/" + sat_id
    return false
}

function calibrate() {
    get('/calibrate')
    return false
}

function coast() {
    get('/coast')
    return false
}