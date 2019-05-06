PORT = 8000

function get(pathname) {
    const Http = new XMLHttpRequest();
    const url = window.location.protocol + '//' + window.location.hostname + ':' + PORT + pathname;
    Http.open("GET", url);
    Http.send();
}

function handleForm() {
    const lat = document.getElementById('latitude').value;
    const long = document.getElementById('longitude').value;
    const sat_id = document.getElementById('sat_id').value;

    const pathname = "/track/" + lat + "/" + long + "/" + sat_id;
    get(pathname);

//    window.location = "/" + lat + "/" + long + "/" + sat_id
    return false;
}

function calibrate() {
    get('/calibrate');
    return false;
}

function coast() {
    get('/coast');
    return false;
}

function handle_driver_form() {
    const azi = document.getElementById('azimuth').value;
    const alt = document.getElementById('altitude').value;

    const pathname = "/driver/" + azi + "/" + alt;
    get(pathname);
    return false;
}

function update() {
    const Http = new XMLHttpRequest();
    Http.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            var obj = JSON.parse(this.responseText);
            table = document.createElement('table');
            for (var key in obj) {
                var tr = document.createElement('tr');
                var td0 = document.createElement('td');
                td0.appendChild(document.createTextNode(key));
                tr.appendChild(td0);
                var td1 = document.createElement('td');
                td1.appendChild(document.createTextNode(obj[key]));
                tr.appendChild(td1);
                table.appendChild(tr);
            }
            var stat = document.getElementById("status");
            stat.innerHTML = '';
            stat.appendChild(table);
        }
    };
    Http.open("GET", "/status");
    Http.send();
}

function run_status() {
    setInterval(update, 2000);
}