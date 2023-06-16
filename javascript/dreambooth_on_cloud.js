// Sagemaker Train!

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function getElementByXpath(path) {
    console.log(path)
    return document.evaluate(path, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
}

function set_dropdown_value(xpath, value) {
    let dropdown = getElementByXpath(xpath)
    console.log("Trying to click the dropdown " + dropdown)
    dropdown.click()
    let target_dropdown = getElementByXpath(`//ul[contains(.,'${value}')]`)
    console.log("Trying to set the value of dropdown" + target_dropdown)
    target_dropdown.click()
}

async function db_start_sagemaker_train() {
    console.log("Sagemaker training");
    console.log(arguments);
    // var xpath = "//*[@id='cloud_db_model_name']/label/div/div[1]/div"
    // var value = "dummy_local_model"
    // set_dropdown_value(xpath, value)

    // pop up confirmation for sagemaker training
    let do_save = confirm("Confirm to start Sagemaker training? This will take a while.");
    if (do_save == false) {
        return;
    }
    save_config();
    await sleep(1000);
    // let sagemaker_train = gradioApp().getElementById("db_sagemaker_train");
    // sagemaker_train.style.display = "block";
    return filterArgs(4, arguments)
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
        do_save = alert("Please change another model name, only letter and number are allowed");
    }
    let filtered_args = filterArgs(9, arguments);
    console.log(arguments)
    return filtered_args
    // return arguments
}