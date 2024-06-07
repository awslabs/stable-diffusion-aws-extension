import {app} from '../../scripts/app.js'
import {api} from '../../scripts/api.js';
import { ComfyDialog } from "../../scripts/ui/dialog.js";
import { $el } from "../../scripts/ui.js";

let container = null;
let lockCanvas = null;
let selectedItem = null;

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
    button.style.backgroundColor = '#232f3e'; // Dark background color
    button.style.color = '#fff'; // Light white color
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
        button.style.backgroundColor = '#cbd3da'; // Lighter background color on hover
    });

    button.addEventListener('mouseleave', () => {
        button.style.backgroundColor = '#232f3e'; // Reset to original dark background color
    });

    button.addEventListener('click', onClick);
    return button;
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

function createScrollList() {
    const outerContainer = document.createElement('div');
    outerContainer.style.display = 'flex';
    outerContainer.style.flexDirection = 'column';
    outerContainer.style.height = '160px';
    outerContainer.style.marginTop = '8px';
    outerContainer.style.marginLeft = '8px';
    outerContainer.style.width = '90%';

    const toolbarContainer = createToolbar();

    container = document.createElement('div');
    container.style.height = '100%';
    container.style.overflow = 'auto';
    container.style.border = '1px solid #949494';
    container.style.position = 'relative'; // Add this line to position the background text

    // Add the background text
    const backgroundText = document.createElement('div');
    backgroundText.textContent = 'Please create workflow';
    backgroundText.style.position = 'absolute';
    backgroundText.style.top = '50%';
    backgroundText.style.left = '50%';
    backgroundText.style.transform = 'translate(-50%, -50%)';
    backgroundText.style.color = '#949494';
    backgroundText.style.fontSize = '16px';
    backgroundText.style.fontWeight = '600';
    backgroundText.style.pointerEvents = 'none'; // Ensure the text doesn't interfere with click events
    container.appendChild(backgroundText);

    outerContainer.appendChild(toolbarContainer);
    outerContainer.appendChild(container);

    return outerContainer;
}


function createToolbar() {
    const toolbarContainer = document.createElement('div');
    toolbarContainer.style.display = 'flex';
    toolbarContainer.style.justifyContent = 'space-between';
    toolbarContainer.style.backgroundColor = '#232f3e'; // Dark background color
    toolbarContainer.style.padding = '3px';
    toolbarContainer.style.position = 'sticky';
    toolbarContainer.style.top = '0';
    toolbarContainer.style.zIndex = '1';

    toolbarContainer.appendChild(createToolbarButton('&#10010;', handleReleaseButtonClick));
    toolbarContainer.appendChild(createButtonSeparator());
    toolbarContainer.appendChild(createToolbarButton('&#8635;', handleRefreshButtonClick));
    toolbarContainer.appendChild(createButtonSeparator());
    toolbarContainer.appendChild(createToolbarButton('&#10003;', handleChooseButtonClick));
    toolbarContainer.appendChild(createButtonSeparator());
    toolbarContainer.appendChild(createToolbarButton('&#10005;', handleDeleteButtonClick));

    return toolbarContainer;
}

function handleReleaseButtonClick() {
    var dialog = new ModalReleaseDialog(app);
    dialog.show();
}

async function handleRefreshButtonClick() {
    if (lockCanvas == null) {
        lockCanvas = new ModalBlankDialog(app, "Refreshing workflows...");
    }
    lockCanvas.show();
    // Clear the container
    container.innerHTML = '';

    // Add a loading indicator
    const loadingIndicator = document.createElement('div');
    loadingIndicator.textContent = 'Loading...';
    loadingIndicator.style.textAlign = 'center';
    loadingIndicator.style.padding = '20px';
    container.appendChild(loadingIndicator);

    try {
        const response = await api.fetchApi("/workflows");
        const data = await response.json();

        // Clear the loading indicator
        container.innerHTML = '';

        data.workflows.forEach(workflow => {
            const itemContainer = createWorkflowItem(workflow, () => {
                if (selectedItem) {
                    selectedItem.style.backgroundColor = '#f8f9fa'; // Reset previous selection
                }
                itemContainer.style.backgroundColor = '#cbd3da'; // Highlight the selected item
                selectedItem = itemContainer;
            });
            container.appendChild(itemContainer);
        });
    } catch (error) {
        // Clear the loading indicator
        container.innerHTML = '';

        // Display an error message
        const errorMessage = document.createElement('div');
        errorMessage.textContent = 'Error occurred while fetching workflows. Please try again later.';
        errorMessage.style.textAlign = 'center';
        errorMessage.style.padding = '20px';
        container.appendChild(errorMessage);

        console.error('Error occurred while fetching workflows:', error);
    }
    lockCanvas.close();
}


async function handleChooseButtonClick() {
    if (selectedItem) {
        var dialog = new ModalConfirmDialog(app, 'Do you want to change current workflow?', () => {
            var dialog = new ModalBlankDialog(app);
            dialog.show();
        });
        dialog.show();
    } else {
        var dialog = new ModalMessageDialog(app, 'Please select a workflow in the list');
        dialog.show();
    }

}

async function handleDeleteButtonClick() {
    if (selectedItem) {
        var dialog = new ModalConfirmDialog(app, 'Do you want to delete the workflow?', async () => {
            try {
                var target = {
                    'name': selectedItem.firstChild.firstChild.textContent
                };
                const response = await api.fetchApi("/workflows", {
                    method: 'DELETE',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(target)
                });
                const result = await response.json();
            } catch (exception) {
                console.error('Error occurred during restore:', exception);
                alert('An error occurred during restore. Please try again later.');
            }
        });
        dialog.show();
        selectedItem.remove();
        selectedItem = null;
    } else {
        var dialog = new ModalMessageDialog(app, 'Please select a workflow in the list');
        dialog.show();
    }

}


function createToolbarButton(icon, onClick, altText) {
    const button = document.createElement('button');
    button.innerHTML = icon;
    button.style.padding = '6px 12px'; // Increased padding for a more modern look
    button.style.borderRadius = '4px'; // Rounded corners for a modern look
    button.style.border = 'none'; // Remove the default border
    button.style.backgroundColor = '#232f3e'; // Dark background color
    button.style.color = '#fff'; // Light white color
    button.style.fontWeight = '600'; // Semibold font weight
    button.style.cursor = 'pointer'; // Change cursor to a pointer on hover
    button.style.transition = 'background-color 0.3s ease'; // Smooth transition on hover
    button.style.width = '40px'; // Set the fixed width
    button.style.display = 'flex';
    button.style.justifyContent = 'center';
    button.style.alignItems = 'center';
    button.style.fontSize = '14px';
    button.setAttribute('alt', altText); // Add the alt attribute

    // Add hover effect
    button.addEventListener('mouseenter', () => {
        button.style.backgroundColor = '#cbd3da'; // Lighter background color on hover
    });

    button.addEventListener('mouseleave', () => {
        button.style.backgroundColor = '#232f3e'; // Reset to original dark background color
    });

    button.addEventListener('click', onClick);
    return button;
}


function createButtonSeparator() {
    const buttonSeparator = document.createElement('div');
    buttonSeparator.style.width = '1px';
    buttonSeparator.style.height = '24px';
    buttonSeparator.style.backgroundColor = '#949494'; // Light gray color
    return buttonSeparator;
}

function createWorkflowItem(workflow, onClick) {
    const itemContainer = document.createElement('div');
    itemContainer.style.display = 'flex';
    itemContainer.style.alignItems = 'flex-start'; // Align items to the top
    itemContainer.style.justifyContent = 'space-between';
    itemContainer.style.padding = '2px';
    itemContainer.style.borderBottom = '1px solid #949494';
    itemContainer.style.backgroundColor = '#f8f9fa'; // Default background color
    itemContainer.style.position = 'relative'; // Add this line to position the label
    itemContainer.addEventListener('click', onClick);

    const labelContainer = document.createElement('div');
    labelContainer.style.display = 'flex';
    labelContainer.style.flexDirection = 'column';
    labelContainer.style.alignItems = 'flex-start'; // Align labels to the left
    labelContainer.style.zIndex = '1'; // Add this line to ensure the label is on top of the background text

    const nameLabel = document.createElement('span');
    nameLabel.textContent = `${workflow.name}`;
    if (workflow.status == 'Enabled') {
        nameLabel.style.fontWeight = '600';
    }else{
        nameLabel.style.fontWeight = '200';
    }
    nameLabel.style.color = '#212529';
    nameLabel.style.marginBottom = '2px';

    const sizeLabel = document.createElement('span');
    sizeLabel.textContent = `${workflow.size} MB`;
    sizeLabel.style.fontWeight = '300';
    sizeLabel.style.color = '#6c757d';
    sizeLabel.style.fontSize = '12px';
    sizeLabel.style.marginBottom = '2px';

    const createTimeLabel = document.createElement('span');
    const createTime = new Date(workflow.create_time);
    const formattedCreateTime = `${createTime.toISOString().slice(0, 19).replace('T', ' ')}`;
    createTimeLabel.textContent = formattedCreateTime;
    createTimeLabel.style.fontWeight = '300';
    createTimeLabel.style.color = '#6c757d';
    createTimeLabel.style.fontSize = '12px';
    createTimeLabel.style.marginBottom = '2px';


    labelContainer.appendChild(nameLabel);
    labelContainer.appendChild(sizeLabel);
    labelContainer.appendChild(createTimeLabel);
    itemContainer.appendChild(labelContainer);
    return itemContainer;
}

async function handleCheckboxChange(event) {
    console.log(`Checkbox ${event.target.checked ? 'checked' : 'unchecked'}`);
    // Handle checkbox change
    changeOnAWS(event.target.checked);
    // const response = await api.fetchApi("/get_env");
    // const data = await response.json();
    // event.target.checked = data.env.toUpperCase() === 'FALSE';
}


const awsConfig = {
    name: 'awsConfig',
    async setup(app) {
        //       const check_response = await api.fetchApi("/check_is_master");
        //       const check_data = await check_response.json();
        const widgetsContainer = createConfigDiv();

        if (true) {
            const response = await api.fetchApi("/get_env");
            const data = await response.json();

            const checkboxSageMaker = createCheckboxOption('Cloud Prompt', 'options', data.env.toUpperCase() === 'FALSE', handleCheckboxChange);
            widgetsContainer.appendChild(checkboxSageMaker);
        }
        if (true) {
            const scrollList = createScrollList();
            widgetsContainer.appendChild(scrollList);
        }
        if (true) {
            const syncButton = createButton('Release Workflow', handleReleaseButtonClick);
            widgetsContainer.appendChild(syncButton);
        }
        const restartButton = createButton('Restart ComfyUI', restartAPI);
        widgetsContainer.appendChild(restartButton);
        if (true) {
            const restoreButton = createButton('Reset to default', restore);
            widgetsContainer.appendChild(restoreButton);
        }
        app.ui.menuContainer.appendChild(widgetsContainer);
        handleRefreshButtonClick();
    }
}

app.registerExtension(awsConfig);

api.addEventListener("ui_lock", ({ detail }) => {
    if (detail.lock) {
        if (lockCanvas == null) {
            lockCanvas = new ModalBlankDialog(app, "Processing workflows...");
        }
        lockCanvas.show();
        localStorage.setItem("ui_lock_status", "locked");
    }
});

// Close ui_lock listener
api.addEventListener("ui_lock", ({ detail }) => {
    if (!detail.lock) {
        if (lockCanvas != null) {
            lockCanvas.close();
            localStorage.setItem("ui_lock_status", "unlocked");
        }
    }
});

// Restore ui_lock status on page load
window.addEventListener("load", () => {
    const uiLockStatus = localStorage.getItem("ui_lock_status");
    if (uiLockStatus === "locked") {
        if (lockCanvas == null) {
            lockCanvas = new ModalBlankDialog(app, "Processing workflows...");
        }
        lockCanvas.show();
    }
});

// Blank modal dialog, show a close button after 10 seconds
export class ModalBlankDialog extends ComfyDialog {
	constructor(app, message) {
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
						{ textContent: message },
					),
					$el(
						"tr",
						{
							style: { display: "none" },
						},
						[$el("th"), $el("th", { style: { width: "23%" } })]
					),
				]),
				$el(
					"div",
					{
						id: "close-button",
						style: {
							position: "fixed",
							top: "10px",
							right: "10px",
							display: "none",
						},
					},
					[
						$el("button", {
							textContent: "X",
							onclick: () => this.element.close(),
						}),
					]
				),
			]
		);

		setTimeout(() => {
			document.getElementById("close-button").style.display = "block";
		}, 10000);
	}

	show() {
		this.element.showModal();
	}

    close() {
		this.element.close();
	}
}



// input field dialog
export class ModalReleaseDialog extends ComfyDialog {
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
                        { textContent: "Release Workflow" },
                    ),
                    $el(
                        "tr",
                        [
                            $el("th", { textContent: "Workflow Name" }),
                            $el("td", [
                                $el("input", {
                                    type: "text",
                                    id: "input-field",
                                    style: { width: "100%" },
                                }),
                            ]),
                        ]
                    ),
                    $el(
                        "tr",
                        [
                            $el("td", { colspan: 2, style: { textAlign: "center" } }, [
                                $el("button", {
                                    id: "ok-button",
                                    textContent: "OK",
                                    style: { marginRight: "10px" },
                                    onclick: () => this.handleOkClick(),
                                }),
                                $el("button", {
                                    id: "cancel-button",
                                    textContent: "Cancel",
                                    onclick: () => this.handleCancelClick(),
                                }),
                            ]),
                        ]
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

    getInputValue() {
        return document.getElementById("input-field").value;
    }

    async handleOkClick() {
        this.element.close();
        try {
            var target = {
                'name': this.getInputValue(),
                'payload_json': "workflow test payload"
            };
            const response = await api.fetchApi("/workflows", {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(target)
            });
            const result = await response.json();
        } catch (exception) {
            console.error('Error occurred during restore:', exception);
            alert('An error occurred during restore. Please try again later.');
        }
    }

    handleCancelClick() {
        this.element.close();
    }
}


export class ModalConfirmDialog extends ComfyDialog {
    constructor(app, message, callback) {
        super();
        this.app = app;
        this.message = message;
        this.callback = callback;
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
                        { textContent: "Confirmation" },
                    ),
                    $el(
                        "tr",
                        [
                            $el("td", { colspan: 2, style: { textAlign: "center" } }, [
                                $el("p", { textContent: this.message, style: { textAlign: "center" } }),
                            ]),
                        ]
                    ),
                    $el(
                        "tr",
                        [
                            $el("td", { colspan: 2, style: { textAlign: "center" } }, [
                                $el("button", {
                                    id: "ok-button",
                                    textContent: "Yes",
                                    style: { marginRight: "10px" },
                                    onclick: () => this.handleYesClick(),
                                }),
                                $el("button", {
                                    id: "cancel-button",
                                    textContent: "No",
                                    onclick: () => this.handleNoClick(),
                                }),
                            ]),
                        ]
                    ),
                ]),
            ]
        );
    }

    show() {
        this.element.showModal();
    }

    handleYesClick() {
        // Add your logic for the Yes button here
        this.callback();
        this.element.close();
    }

    handleNoClick() {
        this.element.close();
    }
}



export class ModalMessageDialog extends ComfyDialog {
    constructor(app, message) {
        super();
        this.app = app;
        this.message = message;
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
                        { textContent: "Information" },
                    ),
                    $el(
                        "tr",
                        [
                            $el("td", { colspan: 2, style: { textAlign: "center" } }, [
                                $el("p", { textContent: this.message, style: { textAlign: "center" } }),
                            ]),
                        ]
                    ),
                    $el(
                        "tr",
                        [
                            $el("td", { colspan: 2, style: { textAlign: "center" } }, [
                                $el("button", {
                                    id: "ok-button",
                                    textContent: "OK",
                                    onclick: () => this.handleOkClick(),
                                }),
                            ]),
                        ]
                    ),
                ]),
            ]
        );
    }

    show() {
        this.element.showModal();
    }

    handleOkClick() {
        this.element.close();
    }
}

