import {app} from '../../scripts/app.js'
import {api} from '../../scripts/api.js';


export function rebootAPI() {
    if (confirm("Are you sure you'd like to reboot the server?")) {
        try {
            api.fetchApi("/reboot");
        } catch (exception) {

        }
        return true;
    }
    return false;
}

export async function syncEnv() {
    if (confirm("Are you sure you'd like to sync your local environment to AWS?")) {
        try {
            var target = {}
            const response = await api.fetchApi("/sync_env", {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(target)
            });
            const result = await response.json();
            console.log(result)
            if (response.ok) {
                // 如果请求成功，显示成功消息
                alert('Sync completed successfully!');
            } else {
                // 如果请求失败，显示错误消息
                alert('Sync failed. Please try again later.');
            }
        } catch (exception) {
            console.error('Error occurred during sync:', exception);
            alert('An error occurred during sync. Please try again later.');
        }
        return true;
    }
    return false;
}


export async function changeOnAWS(disableAWS) {
    var target
    console.log(disableAWS)
    if(disableAWS === true) {
        if (confirm("Are you sure you'd like to execute your workflow on AWS?")) {
            try {
                target = {'DISABLE_AWS_PROXY': true}
                const response = await api.fetchApi("/change_env", {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(target)
                });
            } catch (exception) {
            }
            return true;
        }
    }
    else {
        if (confirm("Are you sure you'd like to execute your workflow on Local?")) {
          try {
            target = {'DISABLE_AWS_PROXY': false}
            const response = await api.fetchApi("/change_env", {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify(target)
            });
          } catch (exception) {

          }
          return true;
        }
    }
    return false;
}

function createButton(text, onClick) {
    const button = document.createElement('button');
    button.textContent = text;
    button.style.padding = '5px 10px';
    button.style.margin = '5px';
    button.addEventListener('click', onClick);
    return button;
}

function createCheckboxOption(labelText, name, checked, onChange) {
    const label = document.createElement('label');
    label.textContent = labelText;

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.name = name;
    checkbox.checked = checked;
    checkbox.addEventListener('change', onChange);

    label.appendChild(checkbox);
    return label;
}

function createRadioOption(labelText, name, value, onChange, checked = false) {
    const label = document.createElement('label');
    label.textContent = labelText;

    const radio = document.createElement('input');
    radio.type = 'radio';
    radio.name = name;
    radio.value = value;
    radio.checked = checked;
    radio.addEventListener('change', onChange);

    label.appendChild(radio);
    return label;
}

function handleButtonClick() {
    // Call the backend Python function here
    // You can use the `api` module to make a request to the backend
    console.log('Button clicked! Calling backend function...');
    // Reboot system
}

function handleCheckboxChange(event) {
    console.log(`Checkbox ${event.target.checked ? 'checked' : 'unchecked'}`);
    // Handle checkbox change
    changeOnAWS(event.target.checked);
}

function handleRadioChange(event) {
    console.log(`Selected option: ${event.target.value}`);
    // Handle radio option change
    changeOnAWS(event.target.value);
}

const customButton = {
    name: 'CustomButton',
    async setup(app) {
        // const radioOption1 = createRadioOption('AWS', 'options', false, handleRadioChange, true);
        // app.ui.menuContainer.appendChild(radioOption1);
        //
        // const radioOption2 = createRadioOption('Local', 'options', true, handleRadioChange);
        // app.ui.menuContainer.appendChild(radioOption2);

        // Create a container for radio buttons
        // const radioContainer = document.createElement('div');
        // radioContainer.style.display = 'inline-flex';
        // radioContainer.appendChild(radioOption1);
        // radioContainer.appendChild(radioOption2);
        // app.ui.menuContainer.appendChild(radioContainer);

        const checkboxOption1 = createCheckboxOption('On SageMaker', 'options', false, handleCheckboxChange);
        // const checkboxOption2 = createCheckboxOption('Local', 'options', false, handleCheckboxChange);
        const checkboxContainer = document.createElement('div');
        checkboxContainer.style.display = 'flex';
        checkboxContainer.appendChild(checkboxOption1);
        // checkboxContainer.appendChild(checkboxOption2);
        app.ui.menuContainer.appendChild(checkboxContainer);

        const restartButton = createButton('Restart', rebootAPI);
        app.ui.menuContainer.appendChild(restartButton);
        const syncButton = createButton('Synchronize', syncEnv);
        app.ui.menuContainer.appendChild(syncButton);
    },
};

app.registerExtension(customButton);