import {app} from '../../scripts/app.js'
import {api} from '../../scripts/api.js';
import { ComfyDialog } from "../../scripts/ui/dialog.js";
import { $el } from "../../scripts/ui.js";

var container = null;
var lockCanvas = null;
var selectedItem = null;
var lockTimeout = 10000; // 10 seconds
var errorMessage = 'An error occurred, please try again later.';

export function restartAPI() {

    var dialog = new ModalConfirmDialog(app, 'Do you want to RESTART the ComfyUI?', async () => {
        try {
            api.fetchApi("/restart");
        } catch (exception) {
            console.error('Restart error:', exception);
            alert(errorMessage);
        }
    });
    dialog.show();
}

export async function restore() {

    var dialog = new ModalConfirmDialog(app, 'Do you want to RESET the local environment?', async () => {
        try {
            var target = {};
            const response = await api.fetchApi("/restore", {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(target)
            });
            const result = await response.json();
            if (response.ok) {
                alert('Reset local environment successful.');
            } else {
                alert(errorMessage);
            }
        } catch (exception) {
            console.error('Reset error:', exception);
            alert(errorMessage);
        }
    });
    dialog.show();
}

export async function changeOnAWS(disableAWS) {
    var target
    if (disableAWS === false) {
        var dialog = new ModalConfirmDialog(app, 'Do you want to DISABLE cloud prompt?', async () => {
            try {
                target = {'DISABLE_AWS_PROXY': "True"}
                const response = await api.fetchApi("/change_env", {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(target)
                });
            } catch (exception) {
            }
        });
        dialog.show();
    } else {
        var dialog = new ModalConfirmDialog(app, 'Do you want to ENABLE cloud prompt?', async () => {
            try {
                target = {'DISABLE_AWS_PROXY': "False"}
                const response = await api.fetchApi("/change_env", {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(target)
                });
            } catch (exception) {
            }
        });
        dialog.show();
    }
    return disableAWS;
}

function alert(message) {
    var messageDialog = new ModalMessageDialog(app, message);
    messageDialog.show();
}

function createButton(text, onClick) {
    const button = document.createElement('button');
    button.textContent = text;
    button.style.padding = '4px 12px';
    button.style.borderRadius = '4px';
    button.style.border = 'none';
    button.style.backgroundColor = '#232f3e';
    button.style.color = '#fff';
    button.style.fontWeight = '600';
    button.style.cursor = 'pointer';
    button.style.transition = 'background-color 0.3s ease';
    button.style.width = '90%';
    button.style.marginTop = '4px';
    button.style.whiteSpace = 'nowrap';
    button.style.overflow = 'hidden';
    button.style.textOverflow = 'ellipsis';
    button.style.fontSize = '14px';

    // Add hover effect
    button.addEventListener('mouseenter', () => {
        button.style.backgroundColor = '#cbd3da';
    });

    button.addEventListener('mouseleave', () => {
        button.style.backgroundColor = '#232f3e';
    });

    button.addEventListener('click', onClick);
    return button;
}



function createSageMakerOption(labelText, name, checked, onChange) {
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

function createConfigPanel() {
    const div = document.createElement('div');
    div.style.border = '1px solid #d9d9d9';
    div.style.width = '100%';
    div.style.position = 'relative';
    div.style.paddingTop = '10px';
    div.style.paddingBottom = '10px';
    div.style.marginTop = '20px';
    div.style.borderRadius = '4px';
    div.style.backgroundColor = '#ffffff';

    const label = document.createElement('label');
    label.textContent = 'AWS Config';
    label.style.position = 'absolute';
    label.style.borderRadius = '4px';

    label.style.top = '-8px';
    label.style.left = '32px';
    label.style.backgroundColor = '#ffffff';
    label.style.padding = '4px 4px 0px 4px';
    label.style.fontSize = '14px';
    label.style.fontWeight = '700';
    label.style.color = '#212529';

    // Add the icon
    const icon = document.createElement('span');
    icon.innerHTML = '&#10064;';
    icon.style.marginLeft = '8px';
    icon.style.cursor = 'pointer';
    icon.addEventListener('click', () => toggleConfigPanelPosition(div));
    label.appendChild(icon);

    div.appendChild(label);

    return div;
}

function toggleConfigPanelPosition(div) {
    const menu = document.getElementsByClassName('comfy-menu')[0];
    const menuRect = menu.getBoundingClientRect();
    const moveTop = menuRect.top -  div.getBoundingClientRect().top + 12;
    const moveLeft = 0 - menuRect.width + 4;
    if (div.style.transform === '') {
        div.style.transform = `translate(${moveLeft}px, ${moveTop}px)`;
    } else {
        div.style.transform = '';
    }
}

function createWorkflowList() {
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
    container.style.position = 'relative';

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
    backgroundText.style.pointerEvents = 'none';
    container.appendChild(backgroundText);

    outerContainer.appendChild(toolbarContainer);
    outerContainer.appendChild(container);

    return outerContainer;
}

function createToolbar() {
    const toolbarContainer = document.createElement('div');
    toolbarContainer.style.display = 'flex';
    toolbarContainer.style.justifyContent = 'space-between';
    toolbarContainer.style.backgroundColor = '#232f3e';
    toolbarContainer.style.padding = '3px';
    toolbarContainer.style.position = 'sticky';
    toolbarContainer.style.top = '0';
    toolbarContainer.style.zIndex = '1';

    toolbarContainer.appendChild(createToolbarButton('&#10010;', handleReleaseButton, 'Create New Workflow'));
    toolbarContainer.appendChild(createButtonSeparator());
    toolbarContainer.appendChild(createToolbarButton('&#8635;', handleLoadButton, 'Reload Workflow'));
    toolbarContainer.appendChild(createButtonSeparator());
    toolbarContainer.appendChild(createToolbarButton('&#10003;', handleChangeButton, 'Change Workflow'));
    toolbarContainer.appendChild(createButtonSeparator());
    toolbarContainer.appendChild(createToolbarButton('&#10005;', handleDeleteButton, 'Remove Workflow'));

    return toolbarContainer;
}

function handleReleaseButton() {
    var dialog = new ModalReleaseDialog(app);
    dialog.show();
}

async function handleLoadButton() {
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
        console.log(response);
        const data = await response.json();
        // Clear the loading indicator
        container.innerHTML = '';
        data.data.workflows.forEach(workflow => {
            const itemContainer = createWorkflowItem(workflow, () => {
                if (selectedItem) {
                    selectedItem.style.backgroundColor = '#f8f9fa';
                }
                itemContainer.style.backgroundColor = '#cbd3da';
                selectedItem = itemContainer;
            });
            container.appendChild(itemContainer);
        });
    } catch (error) {
        // Clear the loading indicator
        container.innerHTML = '';

        // Display an error message
        const errorMessage = document.createElement('div');
        errorMessage.textContent = 'Loading error, please try again later.';
        errorMessage.style.textAlign = 'center';
        errorMessage.style.padding = '20px';
        container.appendChild(errorMessage);

        console.error('Loading error:', error);
    }
}


async function handleChangeButton() {
    if (selectedItem) {
        var dialog = new ModalConfirmDialog(app, 'Do you want to CHANGE workflow to "' + selectedItem.firstChild.firstChild.textContent + '" ?', async () => {
            try {
                lockScreen();
                var target = {
                    'name': selectedItem.firstChild.firstChild.textContent
                };
                const response = await api.fetchApi("/workflows", {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(target)
                });
                const result = await response.json();
                unLockScreen();
                alert(result.message);
            } catch (exception) {
                console.error('Change error:', exception);
                alert(errorMessage);
            }
        });
        dialog.show();
    } else {
        alert('Please select a workflow in the list');
    }

}

async function handleDeleteButton() {
    if (selectedItem) {
        var dialog = new ModalConfirmDialog(app, 'Do you want to DELETE the workflow?', async () => {
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
                if (!result.result) {
                    lockCanvas.close();
                    alert(result.message);
                }
            } catch (exception) {
                console.error('Delete error:', exception);
                alert(errorMessage);
            }
        });
        dialog.show();
        selectedItem.remove();
        selectedItem = null;
    } else {
        alert('Please select a workflow in the list');
    }

}

function createToolbarButton(icon, onClick, altText) {
    const button = document.createElement('button');
    button.innerHTML = icon;
    button.style.padding = '6px 12px';
    button.style.borderRadius = '4px';
    button.style.border = 'none';
    button.style.backgroundColor = '#232f3e';
    button.style.color = '#fff';
    button.style.fontWeight = '600';
    button.style.cursor = 'pointer';
    button.style.transition = 'background-color 0.3s ease';
    button.style.width = '40px';
    button.style.display = 'flex';
    button.style.justifyContent = 'center';
    button.style.alignItems = 'center';
    button.style.fontSize = '14px';
    button.setAttribute('alt', altText);
    button.setAttribute('title', altText);

    // Add hover effect
    button.addEventListener('mouseenter', () => {
        button.style.backgroundColor = '#cbd3da';
    });

    button.addEventListener('mouseleave', () => {
        button.style.backgroundColor = '#232f3e';
    });

    button.addEventListener('click', onClick);
    return button;
}


function createButtonSeparator() {
    const buttonSeparator = document.createElement('div');
    buttonSeparator.style.width = '1px';
    buttonSeparator.style.height = '24px';
    buttonSeparator.style.backgroundColor = '#949494';
    return buttonSeparator;
}

function createWorkflowItem(workflow, onClick) {
    const itemContainer = document.createElement('div');
    itemContainer.style.display = 'flex';
    itemContainer.style.alignItems = 'flex-start';
    itemContainer.style.justifyContent = 'space-between';
    itemContainer.style.padding = '2px';
    itemContainer.style.paddingLeft = '4px';
    itemContainer.style.borderBottom = '1px solid #949494';
    itemContainer.style.backgroundColor = '#f8f9fa';
    itemContainer.style.position = 'relative';
    itemContainer.addEventListener('click', onClick);

    const labelContainer = document.createElement('div');
    labelContainer.style.display = 'flex';
    labelContainer.style.flexDirection = 'column';
    labelContainer.style.alignItems = 'flex-start';
    labelContainer.style.zIndex = '1';
    labelContainer.setAttribute('alt', workflow.payload_json);
    labelContainer.setAttribute('title', workflow.payload_json);

    const nameLabel = document.createElement('span');
    nameLabel.textContent = `${workflow.name}`;
    if (workflow.in_use) {
        nameLabel.style.fontWeight = '600';
    }else{
        nameLabel.style.fontWeight = '200';
    }
    nameLabel.style.color = '#212529';
    nameLabel.style.marginBottom = '2px';

    const sizeLabel = document.createElement('span');
    sizeLabel.textContent = workflow.size ? `${workflow.size} GB` : "unknow";
    sizeLabel.style.fontWeight = '300';
    sizeLabel.style.color = '#6c757d';
    sizeLabel.style.fontSize = '12px';
    sizeLabel.style.marginBottom = '2px';

    // const createTimeLabel = document.createElement('span');
    // const createTime = new Date(workflow.create_time);
    // const formattedCreateTime = `${createTime.toISOString().slice(0, 19).replace('T', ' ')}`;
    // createTimeLabel.textContent = formattedCreateTime;
    // createTimeLabel.style.fontWeight = '300';
    // createTimeLabel.style.color = '#6c757d';
    // createTimeLabel.style.fontSize = '12px';
    // createTimeLabel.style.marginBottom = '2px';


    labelContainer.appendChild(nameLabel);
    labelContainer.appendChild(sizeLabel);
    // labelContainer.appendChild(createTimeLabel);
    itemContainer.appendChild(labelContainer);
    return itemContainer;
}

async function handlePromptChange(event) {
    console.log(`Checkbox ${event.target.checked ? 'checked' : 'unchecked'}`);
    // Handle checkbox change
    changeOnAWS(event.target.checked);
    // const response = await api.fetchApi("/get_env");
    // const data = await response.json();
    // event.target.checked = data.env.toUpperCase() === 'FALSE';
}


const awsConfigPanel = {
    name: 'awsConfigPanel',
    async setup(app) {
        const check_response = await api.fetchApi("/check_is_master");
        const check_data = await check_response.json();
        const isMaster = check_data.master;
        const widgetsContainer = createConfigPanel();

        if (isMaster) {
            const response = await api.fetchApi("/get_env");
            const data = await response.json();

            const checkboxSageMaker = createSageMakerOption('Prompt on AWS', 'options', data.env.toUpperCase() === 'FALSE', handlePromptChange);
            widgetsContainer.appendChild(checkboxSageMaker);
        }

        if (isMaster) {
            const scrollList = createWorkflowList();
            widgetsContainer.appendChild(scrollList);
        }

        if (isMaster) {
            const syncButton = createButton('New Workflow', handleReleaseButton);
            widgetsContainer.appendChild(syncButton);
        }

        const restartButton = createButton('Restart ComfyUI', restartAPI);
        widgetsContainer.appendChild(restartButton);

        if (isMaster) {
            const restoreButton = createButton('Reset to default', restore);
            widgetsContainer.appendChild(restoreButton);
        }

        app.ui.menuContainer.appendChild(widgetsContainer);
        handleLoadButton();
    }
}

app.registerExtension(awsConfigPanel);

function lockScreen() {
        if (lockCanvas == null) {
            lockCanvas = new ModalBlankDialog(app, "Processing workflows...");
        }
        lockCanvas.show();
        localStorage.setItem("ui_lock_status", "locked");
}

function unLockScreen() {
    if (lockCanvas != null) {
        lockCanvas.close();
        localStorage.setItem("ui_lock_status", "unlocked");
    }
}

api.addEventListener("ui_lock", ({ detail }) => {
    if (detail.lock) {
        lockScreen();
    }
});

// Close ui_lock listener
api.addEventListener("ui_lock", ({ detail }) => {
    if (!detail.lock) {
        unLockScreen();
    }
});

// Restore ui_lock status on page load
window.addEventListener("load", () => {
    const uiLockStatus = localStorage.getItem("ui_lock_status");
    if (uiLockStatus === "locked") {
        lockScreen();
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
		}, lockTimeout);
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
                        { textContent: "Release Workflow", style: { border: "0" } },
                    ),
                    $el(
                        "tr",
                        [
                            $el("th", { textContent: "Workflow Name", style: { border: "0" } }),
                            $el("td", [
                                $el("input", {
                                    type: "text",
                                    id: "input-field",
                                    style: { width: "100%", border: "0" },
                                }),
                            ]),
                        ]
                    ),
                    $el(
                        "tr",
                        [
                            $el("td", { colspan: 2, style: { textAlign: "center", border: "0" } }, [
                                $el("button", {
                                    id: "ok-button",
                                    textContent: "OK",
                                    style: { marginRight: "10px", width: "60px" },
                                    onclick: () => this.releaseWorkflow(),
                                }),
                                $el("button", {
                                    id: "cancel-button",
                                    textContent: "Cancel",
                                    style: { marginRight: "10px", width: "60px" },
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

    async releaseWorkflow() {
        this.element.close();
        if (lockCanvas == null) {
            lockCanvas = new ModalBlankDialog(app, "Creating workflow...");
        }
        lockCanvas.show();
        localStorage.setItem("ui_lock_status", "locked");
        try {
            let payloadJson = '';
            app.graphToPrompt().then(p=>{
                payloadJson = JSON.stringify(p.workflow, null, 2);
            });

            var target = {
                'name': this.getInputValue(),
                'payload_json': payloadJson
            };
            const response = await api.fetchApi("/workflows", {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(target)
            });
            const result = await response.json();
            if (!result.result) {
                lockCanvas.close();
                alert(result.message);
            }
        } catch (exception) {
            console.error('Create error:', exception);
            lockCanvas.close()
            alert(errorMessage);
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
                        { textContent: "AWS Config" , style: { border: "0" }},
                    ),
                    $el(
                        "tr",
                        [
                            $el("td", { colspan: 2, style: { textAlign: "center", border: "0" } }, [
                                $el("p", { textContent: this.message, style: { textAlign: "center" } }),
                            ]),
                        ]
                    ),
                    $el(
                        "tr",
                        [
                            $el("td", { colspan: 2, style: { textAlign: "center", border: "0"  } }, [
                                $el("button", {
                                    id: "ok-button",
                                    textContent: "Yes",
                                    style: { marginRight: "10px", width: "40px" },
                                    onclick: () => this.handleYesClick(),
                                }),
                                $el("button", {
                                    id: "cancel-button",
                                    textContent: "No",
                                    style: { marginRight: "10px", width: "40px" },
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
                        { textContent: "AWS Config", style: { border: "0" } },
                    ),
                    $el(
                        "tr",
                        [
                            $el("td", { colspan: 2, style: { textAlign: "center", border: "0" } }, [
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
