// Sagemaker Train!
function db_start_sagemaker_train() {
    console.log("Sagemaker training");
    console.log(arguments);

    // pop up confirmation for sagemaker training
    let do_save = confirm("Confirm to start Sagemaker training? This will take a while.");
    if (do_save == false) {
        return;
    }
    save_config();
    // let sagemaker_train = gradioApp().getElementById("db_sagemaker_train");
    // sagemaker_train.style.display = "block";
    return filterArgs(3, arguments)
}

function check_create_model_params() {
    console.log(arguments)
    var re = /^[a-zA-Z0-9](-*[a-zA-Z0-9]){0,30}$/;
    console.log(re.exec(arguments[0]))
    if (arguments[0] == "") {
        do_save = alert("Please add a model name.");
    }
    else if (arguments[1] == "") {
        do_save = alert("Please select a checkpoint");
    }
    else if (re.exec(arguments[0]) == null) {
        do_save = alert("Please change another model name");
    }
    let filtered_args = filterArgs(8, arguments);
    console.log(arguments)
    return filtered_args
    // return arguments
}