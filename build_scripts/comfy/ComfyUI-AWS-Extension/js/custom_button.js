import {app} from '../../scripts/app.js'
import {api} from '../../scripts/api.js';
import { ComfyDialog } from "../../scripts/ui/dialog.js";
import { $el } from "../../scripts/ui.js";

export function restartAPI() {
    if (confirm("Are you sure you'd like to restart the ComfyUI?")) {
        try {
            api.fetchApi("/restart");
        } catch (exception) {

        }
        return true;
    }
    return false;
}

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

export async function restore() {
    if (confirm("Are you sure you'd like to restore your local environment?")) {
        try {
            var target = {};
            const response = await api.fetchApi("/restore", {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(target)
            });
            const result = await response.json();
            if (response.ok) {
                alert('Restore success!');
            } else {
                // 如果请求失败，显示错误消息
                alert('Restore failed. Please try again later.');
            }
        } catch (exception) {
            console.error('Error occurred during restore:', exception);
            alert('An error occurred during restore. Please try again later.');
        }
        return true;
    }
    return false;
}


export async function syncEnv() {
    if (confirm("Are you sure you'd like to sync your local environment to AWS?")) {
        try {
            var target = {};
            const FETCH_TIMEOUT = 1800000; // 30 seconds in milliseconds
            const response = await Promise.race([
                api.fetchApi("/sync_env"),
                new Promise((_, reject) => setTimeout(() => reject(new Error('Fetch timeout')), FETCH_TIMEOUT))
            ]);
            const result = await response.json();
            if (response.ok) {
                const TIMEOUT_DURATION = 1800000; // 30 minutes in milliseconds
                const RETRY_INTERVAL = 5000; // 5 seconds in milliseconds
                let responseCheck;
                let resultCheck;
                const startTime = Date.now();
                while (Date.now() - startTime < TIMEOUT_DURATION) {
                    responseCheck = await api.fetchApi("/check_prepare");
                    resultCheck = await responseCheck.json();
                    if (responseCheck.ok) {
                        alert('Sync success!');
                        return true;
                    }
                    await new Promise(resolve => setTimeout(resolve, RETRY_INTERVAL));
                }
                alert('Sync timeout. Please try again later.');
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


export async function syncEnvNoAlert() {
    try {
        var target = {}
        const FETCH_TIMEOUT = 18000000; // 30 minutes in milliseconds
        const response = await Promise.race([
            api.fetchApi("/sync_env"),
            new Promise((_, reject) => setTimeout(() => reject(new Error('Fetch timeout')), FETCH_TIMEOUT))
        ]);
        const result = await response.json();
        if (response.ok) {
            const TIMEOUT_DURATION = 18000000; // 30 minutes in milliseconds
                const RETRY_INTERVAL = 5000; // 5 seconds in milliseconds
                let responseCheck;
                let resultCheck;
                const startTime = Date.now();
                while (Date.now() - startTime < TIMEOUT_DURATION) {
                    responseCheck = await api.fetchApi("/check_prepare");
                    resultCheck = await responseCheck.json();
                    if (responseCheck.ok) {
                        alert('Sync success!');
                        return true;
                    }
                    await new Promise(resolve => setTimeout(resolve, RETRY_INTERVAL));
                }
                alert('Sync timeout. Please try again later.');
        } else {
            // 如果请求失败，显示错误消息
            alert('Please click your synchronized button then execute prompt.');
        }
    } catch (exception) {
        console.error('Error occurred during sync:', exception);
        alert('Please click your synchronized button then try again later.');
    }
}


export async function changeOnAWS(disableAWS) {
    var target
    if (disableAWS === false) {
        if (confirm("Are you sure you'd like to execute your workflow on Local?")) {
            try {
                target = {'DISABLE_AWS_PROXY': "True"}
                const response = await api.fetchApi("/change_env", {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(target)
                });
            } catch (exception) {
            }
            return false;
        }
    } else {
        if (confirm("Are you sure you'd like to execute your workflow on AWS?")) {
            try {
                target = {'DISABLE_AWS_PROXY': "False"}
                const response = await api.fetchApi("/change_env", {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(target)
                });
            } catch (exception) {
            }
            syncEnvNoAlert()
            return true;
        }
    }
    return disableAWS;
}

function createButton(text, onClick) {
    const button = document.createElement('button');
    button.textContent = text;
    button.style.padding = '6px 12px'; // Increased padding for a more modern look
    button.style.borderRadius = '4px'; // Rounded corners for a modern look
    button.style.border = 'none'; // Remove the default border
    button.style.backgroundColor = '#ff9900'; // AWS orange color
    button.style.color = 'white'; // Text color for contrast
    button.style.fontWeight = '600'; // Semibold font weight
    button.style.cursor = 'pointer'; // Change cursor to a pointer on hover
    button.style.transition = 'background-color 0.3s ease'; // Smooth transition on hover
    button.style.width = '90%';
    button.style.marginTop = '5px';
    button.style.whiteSpace = 'nowrap';
    button.style.overflow = 'hidden'; // Hide overflowing text
    button.style.textOverflow = 'ellipsis'; // Add an ellipsis (...) for overflowing text
    button.style.fontSize = '14px';

    // Add hover effect
    button.addEventListener('mouseenter', () => {
        button.style.backgroundColor = '#cc7a00'; // Darker orange on hover
    });

    button.addEventListener('mouseleave', () => {
        button.style.backgroundColor = '#ff9900'; // Reset to original orange
    });

    button.addEventListener('click', onClick);
    return button;
}


function addHr() {
    const hr = document.createElement('hr');
    hr.style.width = '100%';
    return hr;
}
function createList(text, onClick) {
    const container = document.createElement('div');
    container.style.display = 'flex';
    container.style.alignItems = 'center';
    container.style.marginTop = '5px';
    container.style.marginLeft = '10px';
    container.style.width = '90%';

    const label = document.createElement('label');
    label.textContent = 'Workflow';
    label.style.fontWeight = '700';
    label.style.marginRight = '10px';
    label.style.fontSize = '14px';
    label.style.color = '#212529';

    const select = document.createElement('select');
    select.style.padding = '5px 10px';
    select.style.borderRadius = '4px';
    select.style.border = '1px solid #949494';
    select.style.backgroundColor = '#ffffff';
    select.style.color = '#212529';
    select.style.fontSize = '14px';
    // select.addEventListener('click', onClick);

    const localOption = document.createElement('option');
    localOption.value = 'local';
    localOption.textContent = 'Local';
    select.appendChild(localOption);

    const localOption2 = document.createElement('option');
    localOption2.value = 'local';
    localOption2.textContent = 'Local';
    select.appendChild(localOption2);

    container.appendChild(label);
    container.appendChild(select);

    return container;
}


function createCheckboxOption(labelText, name, checked, onChange) {
    const container = document.createElement('div');
    container.style.display = 'flex';
    container.style.alignItems = 'center';
    container.style.marginTop = '5px';
    container.style.marginLeft = '10px';
    container.style.width = '90%';

    const label = document.createElement('label');
    label.textContent = labelText;
    label.style.fontWeight = '700';
    label.style.marginRight = '10px';
    label.style.fontSize = '14px';
    label.style.color = '#212529';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.name = name;
    checkbox.checked = checked;
    checkbox.style.padding = '5px 10px';
    checkbox.style.borderRadius = '4px';
    checkbox.style.border = '1px solid #949494';
    checkbox.style.backgroundColor = '#ffffff';
    checkbox.style.color = '#212529';
    checkbox.style.fontSize = '14px';
    checkbox.addEventListener('change', onChange);

    container.appendChild(label);
    container.appendChild(checkbox);

    return container;
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

function createConfigDiv() {
    const div = document.createElement('div');
    div.style.border = '1px solid #d9d9d9'; // Use a light gray border
    div.style.width = '100%';
    div.style.position = 'relative';
    div.style.paddingTop = '10px'; // Increase padding for better spacing
    div.style.paddingBottom = '10px'; // Increase padding for better spacing
    div.style.marginTop = '20px'; // Increase margin for better spacing
    div.style.borderRadius = '4px'; // Add rounded corners
    div.style.backgroundColor = '#ffffff'; // Set a white background color

    const label = document.createElement('label');
    label.textContent = 'AWS Config';
    label.style.position = 'absolute';
    label.style.borderRadius = '4px'; // Add rounded corners

    label.style.top = '-8px'; // Adjust the top position
    label.style.left = '40px'; // Move the label to the left
    label.style.backgroundColor = '#ffffff'; // Set a white background color
    label.style.padding = '4px 4px 0px 4px'; // Adjust padding
    label.style.fontSize = '14px'; // Set a font size similar to AWS console
    label.style.fontWeight = '700'; // Make the label text bold
    label.style.color = '#212529'; // Use a dark gray color for the label text

    div.appendChild(label);

    return div;
}



function handleButtonClick() {
    // Call the backend Python function here
    // You can use the `api` module to make a request to the backend
    console.log('Button clicked! Calling backend function...');
    // Reboot system
}

async function handleCheckboxChange(event) {
    console.log(`Checkbox ${event.target.checked ? 'checked' : 'unchecked'}`);
    // Handle checkbox change
    changeOnAWS(event.target.checked);
    // const response = await api.fetchApi("/get_env");
    // const data = await response.json();
    // event.target.checked = data.env.toUpperCase() === 'FALSE';
}

function handleRadioChange(event) {
    console.log(`Selected option: ${event.target.value}`);
    // Handle radio option change
    changeOnAWS(event.target.value);
}

const customButton = {
    name: 'CustomButton',
    async setup(app) {
       const check_response = await api.fetchApi("/check_is_master");
       const check_data = await check_response.json();
       const widgetsContainer = createConfigDiv();
        if (check_data.master){
            const response = await api.fetchApi("/get_env");
            const data = await response.json();

            const checkboxSageMaker = createCheckboxOption('On SageMaker', 'options', data.env.toUpperCase() === 'FALSE', handleCheckboxChange);
            widgetsContainer.appendChild(checkboxSageMaker);
            app.ui.menuContainer.appendChild(widgetsContainer);

            const restoreButton = createButton('Restore', restore);
            widgetsContainer.appendChild(restoreButton);

            // const rebootButton = createButton('Reboot EC2', rebootAPI);
            // widgetsContainer.appendChild(rebootButton);

            const syncButton = createButton('Release Workflow', syncEnv);
            widgetsContainer.appendChild(syncButton);

            const workflowList = createList('Release Workflow', syncEnv);
            widgetsContainer.appendChild(workflowList);
        }
        const restartButton = createButton('Restart ComfyUI', restartAPI);
        widgetsContainer.appendChild(restartButton);
    }
}

// Blank modal dialog
export class ComfyBlankModalDialog extends ComfyDialog {
	constructor(app) {
		super();
		this.app = app;
		this.settingsValues = {};
		this.settingsLookup = {};
		this.element = $el(
			"dialog",
			{
				id: "comfy-settings-dialog",
				parent: document.body,
			},
			[
				$el("table.comfy-modal-content.comfy-table", [
					$el(
						"caption",
						{ textContent: "Please wait..." },
					),
				]),
			]
		);
	}

	show() {
		this.textElement.replaceChildren(
			$el(
				"tr",
				{
					style: { display: "none" },
				},
				[$el("th"), $el("th", { style: { width: "33%" } })]
			)
		);
		this.element.showModal();
	}
}
app.registerExtension(customButton);