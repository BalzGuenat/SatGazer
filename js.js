function handleForm() {
    var alt = document.getElementById('latitude').value;
    var long = document.getElementById('longitude').value;
    var sat_id = document.getElementById('sat_id').value;

    window.location = "/" + alt + "/" + long + "/" + sat_id
    return false
}