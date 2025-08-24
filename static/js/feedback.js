$(document).ready(function() {
    const stars = $('.star-rating i');
    const ratingInput = $('#rating');
    const ratingError = $('#rating-error');
    const form = $('#feedback-form');
    const submitBtn = $('#submit-feedback');
    const responseAlert = $('#feedback-response');

    // Star rating logic
    stars.on('click', function() {
        const value = $(this).data('value');
        ratingInput.val(value);
        ratingError.hide();
        stars.each(function() {
            $(this).toggleClass('active', $(this).data('value') <= value);
        });
    });

    stars.on('mouseover', function() {
        const value = $(this).data('value');
        stars.each(function() {
            if ($(this).data('value') <= value) {
                $(this).addClass('hover');
            } else {
                $(this).removeClass('hover');
            }
        });
    });

    stars.on('mouseout', function() {
        stars.removeClass('hover');
    });

    // AJAX form submission
    form.on('submit', function(e) {
        e.preventDefault();
        if (!ratingInput.val()) {
            ratingError.show();
            return;
        }

        submitBtn.html('<i class="fas fa-spinner fa-spin me-2"></i>Submitting...').prop('disabled', true);

        $.ajax({
            url: '/contacts/',
            type: 'POST',
            data: form.serialize(),
            headers: {
                'X-CSRFToken': $('input[name=csrfmiddlewaretoken]').val()
            },
            success: function(response) {
                if (response.status === 'success') {
                    responseAlert
                        .removeClass('d-none alert-danger')
                        .addClass('alert-success')
                        .text(response.message)
                        .show();
                    form[0].reset();
                    stars.removeClass('active');
                    setTimeout(() => {
                        $('#feedbackModal').modal('hide');
                        responseAlert.addClass('d-none').text('');
                    }, 2000);
                } else {
                    responseAlert
                        .removeClass('d-none alert-success')
                        .addClass('alert-danger')
                        .text(response.message)
                        .show();
                    submitBtn.html('<i class="fas fa-paper-plane me-2"></i>Submit Feedback').prop('disabled', false);
                }
            },
            error: function() {
                responseAlert
                    .removeClass('d-none alert-success')
                    .addClass('alert-danger')
                    .text('An error occurred. Please try again.')
                    .show();
                submitBtn.html('<i class="fas fa-paper-plane me-2"></i>Submit Feedback').prop('disabled', false);
            }
        });
    });
});