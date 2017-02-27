$(document).ready(function() {
    // Materialize.updateTextFields();

    // Materialize Select doesn't work with Vue
    $('select').addClass('browser-default');
    // $('select').material_select();
    $('.button-collapse').sideNav();
    $('.modal-trigger').leanModal();
});