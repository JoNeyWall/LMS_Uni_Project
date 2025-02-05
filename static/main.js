import { $ } from "/static/jquery/src/jquery.js";
function say_hi(elt) {
    console.log("Welcome to", elt.text());
}
say_hi($("h1"));

function make_table_sortable(table){
    let $table = $(table)
    let $sorting_cells = $table.find('thead th.sort-column');
    let $table_body = $table.find('tbody');

    //Accessibility feature thing
    $sorting_cells.attr('role', 'button');

    //Sort by column contents
    $sorting_cells.on('click', function() {
        //determine the state of the table
        let $sorting_cell = $(event.currentTarget);
        let column_index = $sorting_cell.index();
        let is_ascending = $sorting_cell.hasClass('sort-asc');
        let is_descending = $sorting_cell.hasClass('sort-desc');

        //Clear the class before operating
        $sorting_cell.removeClass('sort-asc sort-desc').attr('aria-sort', 'none');
        let table_rows = $table_body.find('tr').toArray();

        //Click order: Original -> Descending -> Ascending
        if (is_ascending){            
            $sorting_cells.addClass('sort-desc').attr('aria-sort', 'descending');

            table_rows.sort((first, second) => {
                let first_val = parseFloat($(first).find('td').eq(column_index).data('value')) || 0;
                let second_val = parseFloat($(second).find('td').eq(column_index).data('value')) || 0;
                return second_val - first_val;
            });
        } 
        else if (is_descending) {
            table_rows.sort((first, second) => {
                let first_index = $(first).data("index");
                let second_index = $(second).data("index");
                return first_index - second_index
            });
        } 
        else {
            $sorting_cell.addClass('sort-asc').attr('aria-sort', 'ascending');

            table_rows.sort((first, second) => {
                let first_val = parseFloat($(first).find('td').eq(column_index).data('value')) || 0;
                let second_val = parseFloat($(second).find('td').eq(column_index).data('value')) || 0;
                return first_val - second_val;
            });
        }

        //Sorted by score rows
        $table_body.append(table_rows);
        //Keep the final grade on the bottom
        $table_body.append($table_body.find('.final-grade-row'));
    });
}

//Apply make_table_sortable to tables with class=sortable
$(document).ready(function () {
    make_table_sortable($("table.sortable"));
});

function make_form_async(form) {
    form.on('submit', function(event) {
        //prevent default behavior
        event.preventDefault()

        //Get this form and grab data to make a new FormData object
        let $form = $(form);
        let form_data = new FormData($form[0]);
        //Set button to be disabled
        $form.find('input[type="file"], button').prop('disabled', true);

        //Asynchronous response
        $.ajax({
            url: $form.attr('action'), data:form_data, type:'POST', processData:false, contentType:false, mimeType:$form.attr('enctype'), 
            headers:{
                'X-CSRFToken':$('input[name="csrftoken]').val()
            },
            success:function() {
                //Replace button with success message
                $form.replaceWith('<p>Upload Succeeded, refresh to re-upload.</p>');
            },
            error:function(error) {
                //Log error and make sure the disabled property is false
                console.log('Upload Error: ', error);
                $form.find('input[type="file"], button').prop('disabled', false);
            }
        });
    })
}

//Apply make_form_async to submission form
$(document).ready(function () {
    make_form_async($('form.async-submit'));
});

function make_grade_hypothesized(table) {
    let $table = $(table);
    let $table_body = $table.find('tbody');
    let $final_grade_cell = $table.find('th.final-grade-entry');
    let $h_button = $('<button class="h-button">Hypothesize</button>');

    //Place the button before the table
    $table.before($h_button);

    $h_button.on('click', function() {
        $table.toggleClass('hypothesized');

        if ($table.hasClass('hypothesized')) {
            //Change text on botton
            $h_button.text('Actual Grades');
            $table_body.find('td').each(function() {
                let $cell = $(this);

                if ($cell.text() === 'Not Due' || $cell.text() === "Ungraded"){
                    //Save this to be able to reset the text to Not Due or Ungraded
                    let restore_val = $cell.text();
                    $cell.empty(); //Clear the text from the cell

                    let $input = $('<input type="number" class="hypothesized-input score-entry" placeholder="0" max="100" min="0">');
                    $cell.append($input);
                    
                    //Save for later
                    $input.data('restore', restore_val);
                }
            });
            //Recompute on keyup
            $table_body.find('.hypothesized-input').on('keyup', function() {
                console.log("Keyup called"); //debug
                compute_grade($table);
            });
        }
        else {
            //Reset button to say Hypothesize
            $h_button.text('Hypothesize');

            $table_body.find('td').each(function() {
                let $cell = $(this);
                let $input = $cell.find('.hypothesized-input');

                if ($input.length){
                    //Restore the value that was saved earlier
                    let restore_val = $input.data('restore');
                    $cell.text(restore_val)
                    $input.remove();
                }
            });
            //Recompute with original values
            compute_grade($table);
        }
    }); 

    function compute_grade($table) {
        console.log("compute_grade called"); //debug
        let $table_body = $table.find('tbody');
    
        let total_score = 0;
        let total_score_weight = 0;
    
        //For each row in the table
        $table_body.find('tr').each(function() {
            let $table_row = $(this);
            //Don't use the final score as a datapoint
            if (!($table_row.hasClass('final-grade-entry'))){
                let $score_cell = $table_row.find('td.score-entry');
                //Score is a little more complicated
                let score;
                let weight = parseFloat($score_cell.data('weight'));
                let $input = $score_cell.find('.hypothesized-input');
                console.log("Weight:", weight); //debug
        
                //If hypothesized entry
                if ($input.length) {
                    if ($input.val() !== ''){
                        score = parseFloat($input.val());
                        console.log("computing with ", score); //Debug
                        total_score += (score / 100) * weight;
                        total_score_weight += weight;
                    }
                }
                else {
                    let value = $score_cell.data('value');
                    if (value === 'Missing') {
                        total_score_weight += weight;
                    }
                    else if (value === 'Not Due' || value === 'Ungraded'){
                        //Don't do anything here, these grades shouldn't be considered.
                    }
                    else if (value) {
                        score = parseFloat($score_cell.data('value'));
                        console.log("current score:", score); //Debug
                        total_score += (score / 100) * weight;
                        total_score_weight += weight;
                    }
                }

                //Debug
                console.log("total score: ", total_score);
                console.log("total weight: ", total_score_weight);
            }
        });
    
        let final_grade = (total_score / total_score_weight) * 100;
        $final_grade_cell.text(final_grade.toFixed(1) + '%')
    } 
}

//Apply make_grade_hypothesized to the grade table on the student view of profile
$(document).ready(function() {
    if ($('main').hasClass('profile-student')){
        make_grade_hypothesized($('table.sortable'));
    }
});