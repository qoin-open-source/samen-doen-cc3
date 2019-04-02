function disablePercentage() {
    if ($('#id_reward_percentage').prop('checked')) {
        $('#id_transaction_percentage').removeAttr('disabled');
    } else {
        $('#id_transaction_percentage').prop('disabled', true);
    }
}


$(function() {
    disablePercentage();

    $('#id_reward_percentage').change(function () {
        disablePercentage();
    });
});
