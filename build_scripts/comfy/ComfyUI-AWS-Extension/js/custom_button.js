import { app } from '../../scripts/app.js'
import { api } from '../../scripts/api.js';
import { ComfyDialog } from "../../scripts/ui/dialog.js";
import { $el } from "../../scripts/ui.js";

var container = null;
var lockCanvas = null;
var isMaster = false;
var selectedItem = null;
var lockTimeout = 30000; // 30 seconds
var lockInterval = 2000; // 2  seconds
var errorMessage = 'An error occurred, please try again later.';

let dialogCreateTemplateInstance = null;
let dialogModalBlank = null;
let dialogModalRelease = null;
let dialogEditTemplateInstance= null;


export async function handleRestartButton() {

    var dialog = new ModalConfirmDialog(app, 'Do you want to RESTART the ComfyUI?', async () => {
        try {
            const response = await api.fetchApi("/restart");
            const result = await response.json();
            if (response.result) {
                alert(result.message);
            } else {
                alert(result.message);
            }
        } catch (exception) {
            console.error('Restart error:', exception);
            alert(errorMessage);
        }
    });
    dialog.show();
}

export async function handleResetButton() {

    var dialog = new ModalConfirmDialog(app, 'Do you want to RESET the local environment?', async () => {
        try {
            var target = {};
            const response = await api.fetchApi("/restore", {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(target)
            });
            const result = await response.json();
            if (response.result) {
                alert(result.message);
            } else {
                alert(result.message);
            }
        } catch (exception) {
            console.error('Reset error:', exception);
            alert(errorMessage);
        }
    });
    dialog.show();
}

// export async function changeOnAWS(disableAWS, checkbox) {
//     var target
//     var isChecked = checkbox.checked;
//     if (disableAWS === false) {
//         var dialog = new ModalConfirmDialog(app, 'Do you want to DISABLE cloud prompt?', async () => {
//             try {
//                 target = { 'DISABLE_AWS_PROXY': "True" }
//                 const response = await api.fetchApi("/change_env", {
//                     method: 'POST',
//                     headers: { 'Content-Type': 'application/json' },
//                     body: JSON.stringify(target)
//                 });
//             } catch (exception) {
//             }
//             checkbox.checked = false;
//         });
//         dialog.show();
//     } else {
//         var dialog = new ModalConfirmDialog(app, 'Do you want to ENABLE cloud prompt?', async () => {
//             try {
//                 target = { 'DISABLE_AWS_PROXY': "False" }
//                 const response = await api.fetchApi("/change_env", {
//                     method: 'POST',
//                     headers: { 'Content-Type': 'application/json' },
//                     body: JSON.stringify(target)
//                 });
//             } catch (exception) {
//             }
//             checkbox.checked = true;
//         });
//         dialog.show();
//     }
//     checkbox.checked = !isChecked;
//     return disableAWS;
// }

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

// prompt on aws
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

// config panel
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
    icon.setAttribute('alt', 'Move Panel');
    icon.setAttribute('title', 'Move Panel');
    icon.addEventListener('click', () => toggleConfigPanelPosition(div));
    label.appendChild(icon);

    div.appendChild(label);

    return div;
}

// move the config
function toggleConfigPanelPosition(div) {
    const menu = document.getElementsByClassName('comfy-menu')[0];
    const menuRect = menu.getBoundingClientRect();
    const moveTop = menuRect.top - div.getBoundingClientRect().top + 12;
    const moveLeft = 0 - menuRect.width + 4;

    // Add transition styles
    div.style.transition = 'transform 0.1s ease-in-out';

    if (div.style.transform === '') {
        div.style.transform = `translate(${moveLeft}px, ${moveTop}px)`;
    } else {
        div.style.transform = '';
    }
}


// function createWorkflowList() {
//     const outerContainer = document.createElement('div');
//     outerContainer.style.display = 'flex';
//     outerContainer.style.flexDirection = 'column';
//     outerContainer.style.height = '160px';
//     outerContainer.style.marginTop = '8px';
//     outerContainer.style.marginLeft = '8px';
//     outerContainer.style.width = '90%';
//
//     const toolbarContainer = createToolbar();
//
//     container = document.createElement('div');
//     container.style.height = '100%';
//     container.style.overflow = 'auto';
//     container.style.border = '1px solid #949494';
//     container.style.position = 'relative';
//
//     // Add the background text
//     const backgroundText = document.createElement('div');
//     backgroundText.textContent = 'Please create workflow';
//     backgroundText.style.position = 'absolute';
//     backgroundText.style.top = '50%';
//     backgroundText.style.left = '50%';
//     backgroundText.style.transform = 'translate(-50%, -50%)';
//     backgroundText.style.color = '#949494';
//     backgroundText.style.fontSize = '16px';
//     backgroundText.style.fontWeight = '600';
//     backgroundText.style.pointerEvents = 'none';
//     container.appendChild(backgroundText);
//
//     outerContainer.appendChild(toolbarContainer);
//     outerContainer.appendChild(container);
//
//     return outerContainer;
// }

function createTemplateList() {
    const outerContainer = document.createElement('div');
    outerContainer.style.display = 'flex';
    outerContainer.style.flexDirection = 'column';
    outerContainer.style.height = '160px';
    outerContainer.style.marginTop = '8px';
    outerContainer.style.marginLeft = '8px';
    outerContainer.style.width = '90%';

    const title = document.createElement('div');
    title.textContent = 'Template List';
    title.style.fontSize = '14px';
    title.style.fontWeight = 'bold';
    title.style.color = '#b0b0b0';
    title.style.marginBottom = '0px';
    title.style.backgroundColor = '#f0f0f0';
    title.style.borderRadius = '4px';
    outerContainer.appendChild(title);

    const toolbarContainer = createTemplateToolbar();
    toolbarContainer.style.marginTop = '0';

    container = document.createElement('div');
    container.style.height = '100%';
    container.style.overflow = 'auto';
    container.style.border = '1px solid #949494';
    container.style.position = 'relative';

    // Add the background text
    const backgroundText = document.createElement('div');
    backgroundText.textContent = 'Please create template';
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

// function createToolbar() {
//     const toolbarContainer = document.createElement('div');
//     toolbarContainer.style.display = 'flex';
//     toolbarContainer.style.justifyContent = 'space-between';
//     toolbarContainer.style.backgroundColor = '#232f3e';
//     toolbarContainer.style.padding = '3px';
//     toolbarContainer.style.position = 'sticky';
//     toolbarContainer.style.top = '0';
//     toolbarContainer.style.zIndex = '1';
//     if (isMaster) {
//         toolbarContainer.appendChild(createToolbarButton('&#10010;', handleCreateButton, 'Create New Workflow', isMaster));
//     }
//     toolbarContainer.appendChild(createButtonSeparator());
//     toolbarContainer.appendChild(createToolbarButton('&#8635;', handleLoadButton, 'Reload Workflow', true));
//     toolbarContainer.appendChild(createButtonSeparator());
//     toolbarContainer.appendChild(createToolbarButton('&#10003;', handleChangeButton, 'Change Workflow', true));
//     toolbarContainer.appendChild(createButtonSeparator());
//     if (isMaster) {
//         toolbarContainer.appendChild(createToolbarButton('&#10005;', handleDeleteButton, 'Remove Workflow', isMaster));
//     }
//
//     return toolbarContainer;
// }


function createTemplateToolbar() {
    const toolbarContainer = document.createElement('div');
    toolbarContainer.style.display = 'flex';
    toolbarContainer.style.justifyContent = 'space-between';
    toolbarContainer.style.backgroundColor = '#232f3e';
    toolbarContainer.style.padding = '3px';
    toolbarContainer.style.position = 'sticky';
    toolbarContainer.style.top = '0';
    toolbarContainer.style.zIndex = '1';
    if (isMaster) {
        toolbarContainer.appendChild(createToolbarButton('&#10010;', handleCreateTemplateButton, 'Create', isMaster));
    }
    toolbarContainer.appendChild(createButtonSeparator());
    toolbarContainer.appendChild(createToolbarButton('&#8635;', handleLoadTemplateButton, 'Refresh', true));
    toolbarContainer.appendChild(createButtonSeparator());
    toolbarContainer.appendChild(createToolbarButton('&#10003;', handleChangeTemplateButton, 'Confirm to Switch', true));
    toolbarContainer.appendChild(createButtonSeparator());
    if (isMaster) {
        toolbarContainer.appendChild(createToolbarButton('✎', handleEditTemplateButton, 'Edit', isMaster));
        toolbarContainer.appendChild(createToolbarButton('&#10005;', handleDeleteTemplateButton, 'Delete', isMaster));
    }

    return toolbarContainer;
}


function handleCreateTemplateButton() {
    if (!dialogCreateTemplateInstance) {
        dialogCreateTemplateInstance = new ModalTemplateDialog(app);
    }
    dialogCreateTemplateInstance.populateWorkflowSelectField();
    dialogCreateTemplateInstance.clear();
    dialogCreateTemplateInstance.show();
}


function handleEditTemplateButton() {
    if (selectedItem) {
        if (!dialogEditTemplateInstance) {
            dialogEditTemplateInstance = new ModalEditTemplateDialog(app, selectedItem);
        }
        dialogEditTemplateInstance.populateWorkflowSelectField();
        dialogEditTemplateInstance.clear(selectedItem);
        dialogEditTemplateInstance.show();
    } else {
        alert('Please select a template in the list');
    }
}

function handleCreateButton() {
    if(!dialogModalRelease){
        dialogModalRelease = new ModalEndpointReleaseDialog(app);
    }
    dialogModalRelease.clear();
    dialogModalRelease.show();
}


async function handleLoadTemplateButton() {
    // Clear the container
    container.innerHTML = '';

    // Add a loading indicator
    const loadingIndicator = document.createElement('div');
    loadingIndicator.textContent = 'Loading...';
    loadingIndicator.style.textAlign = 'center';
    loadingIndicator.style.padding = '20px';
    container.appendChild(loadingIndicator);

    try {
        const response = await api.fetchApi("/schemas");
        console.log(response);
        const data = await response.json();
        // Clear the loading indicator
        container.innerHTML = '';
        data.data.schemas.forEach(template => {
            const itemContainer = createTemplateItem(template, () => {
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
            if (workflow.status == 'Enabled') {
                const itemContainer = createWorkflowItem(workflow, () => {
                    if (selectedItem) {
                        selectedItem.style.backgroundColor = '#f8f9fa';
                    }
                    itemContainer.style.backgroundColor = '#cbd3da';
                    selectedItem = itemContainer;
                });
                container.appendChild(itemContainer);
            }
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

async function handleChangeTemplateButton() {
    if (selectedItem) {
        var dialog = new ModalConfirmDialog(app, 'Do you want to CHANGE template to "' + selectedItem.firstChild.firstChild.textContent + '" ?', async () => {
            try {
                const template_name = selectedItem.firstChild.firstChild.textContent
                handleLockScreen();
                const templateValue = selectedItem.firstChild.firstChild.value || 'default';
                var target = {
                    'name': templateValue
                };
                await handleLoadTemplateJson(selectedItem.firstChild.firstChild.dataset.payload);
                const response = await api.fetchApi("/workflows", {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(target)
                });
                const result = await response.json();
                handleUnlockScreen();
                localStorage.setItem("in_use_template", template_name);
                alert(result.message);
            } catch (exception) {
                console.error('Change error:', exception);
                alert(errorMessage);
            }
        });
        dialog.show();
    } else {
        alert('Please select a template in the list');
    }
}

async function handleChangeButton() {
    if (selectedItem) {
        var dialog = new ModalConfirmDialog(app, 'Do you want to CHANGE workflow to "' + selectedItem.firstChild.firstChild.textContent + '" ?', async () => {
            try {
                handleLockScreen();
                var target = {
                    'name': selectedItem.firstChild.firstChild.textContent
                };

                await handleLoadJson(selectedItem.firstChild.firstChild.textContent);
                const response = await api.fetchApi("/workflows", {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(target)
                });
                const result = await response.json();
                handleUnlockScreen();
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


async function handleDeleteTemplateButton() {
    if (selectedItem) {
        var dialog = new ModalConfirmDialog(app, 'Do you want to DELETE the template?', async () => {
            try {
                var target = {
                    'schema_name_list': [selectedItem.firstChild.firstChild.textContent]
                };
                const response = await api.fetchApi("/schemas", {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(target)
                });
                const result = await response.json();
                if (result.result) {
                    selectedItem.remove();
                    selectedItem = null;
                } else {
                    handleUnlockScreen();
                    alert(result.message);
                }
            } catch (exception) {
                console.error('Delete error:', exception);
                alert(errorMessage);
            }
        });
        dialog.show();

    } else {
        alert('Please select a template in the list');
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
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(target)
                });
                const result = await response.json();
                if (result.result) {
                    selectedItem.remove();
                    selectedItem = null;
                } else {
                    handleUnlockScreen();
                    alert(result.message);
                }
            } catch (exception) {
                console.error('Delete error:', exception);
                alert(errorMessage);
            }
        });
        dialog.show();

    } else {
        alert('Please select a workflow in the list');
    }

}

function createToolbarButton(icon, onClick, altText, enabled) {
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
    button.style.width = '30px';
    button.style.display = 'flex';
    button.style.justifyContent = 'center';
    button.style.alignItems = 'center';
    button.style.fontSize = '14px';
    button.setAttribute('alt', altText);
    button.setAttribute('title', altText);
    button.disabled = !enabled;

    if (enabled) {
        // Add hover effect
        button.addEventListener('mouseenter', () => {
            button.style.backgroundColor = '#cbd3da';
        });

        button.addEventListener('mouseleave', () => {
            button.style.backgroundColor = '#232f3e';
        });

        button.addEventListener('click', onClick);
    }
    return button;
}


function createButtonSeparator() {
    const buttonSeparator = document.createElement('div');
    buttonSeparator.style.width = '1px';
    buttonSeparator.style.height = '24px';
    buttonSeparator.style.backgroundColor = '#949494';
    return buttonSeparator;
}

function createTemplateItem(template, onClick) {
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
    labelContainer.setAttribute('alt', template.payload);
    labelContainer.setAttribute('title', template.payload);

    const nameLabel = document.createElement('span');
    nameLabel.textContent = `${template.name}`;
    nameLabel.value = `${template.workflow}`;
    nameLabel.dataset.payload = `${template.payload}`;
    nameLabel.style.display = 'flex';
    nameLabel.style.alignItems = 'center';
    const in_use_template = localStorage.getItem("in_use_template");
    if (in_use_template === `${template.name}` ) {
        nameLabel.style.fontWeight = '600';
        try {
            var target = {
                'clientId': api.initialClientId ?? api.clientId,
                'releaseVersion': `${template.workflow}` || 'default'
            };
            const response = api.fetchApi("/map_release", {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(target)
            });
        } catch (error) {
            console.error('Error checking lock status:', error);
        }
        const greenBall = document.createElement('div');
        greenBall.style.width = '8px';
        greenBall.style.height = '8px';
        greenBall.style.borderRadius = '50%';
        greenBall.style.backgroundColor = 'green';
        greenBall.style.marginRight = '4px';
        nameLabel.insertBefore(greenBall, nameLabel.firstChild);
        nameLabel.click()
    } else {
        nameLabel.style.fontWeight = '200';
    }
    nameLabel.style.color = '#212529';
    nameLabel.style.marginBottom = '2px';

    const sizeLabel = document.createElement('span');
    sizeLabel.textContent = template.workflow ? `${template.workflow} ` : "unbind";
    sizeLabel.style.fontWeight = '300';
    sizeLabel.style.color = template.workflow ? '#6c757d' : '#FFA07A';
    sizeLabel.style.fontSize = '12px';
    sizeLabel.style.marginBottom = '2px';

    labelContainer.appendChild(nameLabel);
    labelContainer.appendChild(sizeLabel);
    itemContainer.appendChild(labelContainer);
    return itemContainer;
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
    nameLabel.style.display = 'flex';
    nameLabel.style.alignItems = 'center';
    if (workflow.in_use) {
        nameLabel.style.fontWeight = '600';
        try {
            var target = {
                'clientId': api.initialClientId ?? api.clientId,
                'releaseVersion': `${workflow.name}`
            };
            const response = api.fetchApi("/map_release", {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(target)
            });
        } catch (error) {
            console.error('Error checking lock status:', error);
        }
        const greenBall = document.createElement('div');
        greenBall.style.width = '8px';
        greenBall.style.height = '8px';
        greenBall.style.borderRadius = '50%';
        greenBall.style.backgroundColor = 'green';
        greenBall.style.marginRight = '4px';
        nameLabel.insertBefore(greenBall, nameLabel.firstChild);
    } else {
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
    // changeOnAWS(event.target.checked, event.target);
    var disableAWS = event.target.checked
    var checkbox = event.target
    var target
    var isChecked = checkbox.checked;
    if (disableAWS === false) {
        var dialog = new ModalConfirmDialog(app, 'Do you want to DISABLE cloud prompt?', async () => {
            try {
                target = { 'DISABLE_AWS_PROXY': "True" }
                const response = await api.fetchApi("/change_env", {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(target)
                });
            } catch (exception) {
            }
            checkbox.checked = false;
        });
        dialog.show();
    } else {
        var dialog = new ModalConfirmDialog(app, 'Do you want to ENABLE cloud prompt?', async () => {
            try {
                target = { 'DISABLE_AWS_PROXY': "False" }
                const response = await api.fetchApi("/change_env", {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(target)
                });
            } catch (exception) {
            }
            checkbox.checked = true;
        });
        dialog.show();
    }
    checkbox.checked = !isChecked;
    return disableAWS;

}

async function handleLoadJson(templateId){
    try {
        const response = await api.fetchApi(`/get_env_template/${templateId}`);
        console.log(response);
        if (response.ok) {
            const promptJson =await response.json();
            if (!promptJson){
                console.info("load default json")
                return
            }
            let jsonContent;
            if (typeof promptJson === 'object') {
                const jsonString = JSON.stringify(promptJson);
                jsonContent = JSON.parse(jsonString);
            } else {
                jsonContent = JSON.parse(promptJson);
            }
            if (jsonContent?.workflow) {
                const workflowJsonString = JSON.stringify(jsonContent.workflow);
                const workflowContent = JSON.parse(workflowJsonString);
                console.log(workflowContent)
                await app.loadGraphData(workflowContent);
                console.log("finished loadGraphData")
            } else {
                console.error(jsonContent);
                console.error("Invalid JSON: missing 'workflow' property when loadGraphData.");
            }
        }else {
            console.info('Loading json none: load default');
        }
        return true
    } catch (error) {
        console.error('Loading error:', error);
        return false
    }
}

async function handleLoadTemplateJson(promptJson){
    try {
        if (!promptJson){
            console.info("load default json")
            return
        }
        let jsonContent;
        if (typeof promptJson === 'object') {
            const jsonString = JSON.stringify(promptJson);
            jsonContent = JSON.parse(jsonString);
        } else {
            jsonContent = JSON.parse(promptJson);
        }
        if (jsonContent?.workflow) {
            const workflowJsonString = JSON.stringify(jsonContent.workflow);
            const workflowContent = JSON.parse(workflowJsonString);
            console.log(workflowContent)
            await app.loadGraphData(workflowContent);
            console.log("finished loadGraphData")
        } else {
            console.error(jsonContent);
            console.error("Invalid JSON: missing 'workflow' property when loadGraphData.");
        }
        return true
    } catch (error) {
        console.error('Loading error:', error);
        return false
    }
}


const awsConfigPanel = {
    name: 'awsConfigPanel',
    async setup(app) {
        const check_response = await api.fetchApi("/check_is_master");
        const check_data = await check_response.json();
        isMaster = check_data.master;
        const widgetsContainer = createConfigPanel();
        if (isMaster) {
            const response = await api.fetchApi("/get_env_new/DISABLE_AWS_PROXY");
            const data = await response.json();

            const checkboxSageMaker = createSageMakerOption('Prompt on AWS', 'options', data.env ? data.env.toUpperCase() === 'FALSE' : false, handlePromptChange);
            widgetsContainer.appendChild(checkboxSageMaker);
        }

        const scrollList = createTemplateList();
        widgetsContainer.appendChild(scrollList);

        if (isMaster) {
            const syncButton = createButton('New Environment', handleCreateButton);
            widgetsContainer.appendChild(syncButton);
        }

        const restartButton = createButton('Restart ComfyUI', handleRestartButton);
        widgetsContainer.appendChild(restartButton);

        if (isMaster) {
            const restoreButton = createButton('Reset to default', handleResetButton);
            widgetsContainer.appendChild(restoreButton);
        }

        app.ui.menuContainer.appendChild(widgetsContainer);
        // handleLoadButton();
        dialogCreateTemplateInstance = new ModalTemplateDialog(app);
        dialogCreateTemplateInstance.populateWorkflowSelectField();
        handleLoadTemplateButton();
    }
}

app.registerExtension(awsConfigPanel);

function handleLockScreen(message) {
    if (lockCanvas == null) {
        if (!dialogModalBlank){
            lockCanvas = new ModalBlankDialog(app, message ? message : "Create processing...");
        }else {
            dialogModalBlank.reset_msg(message)
            lockCanvas = dialogModalBlank
        }
    }
    lockCanvas.show();
    localStorage.setItem("ui_lock_status", "locked");
}

function handleUnlockScreen() {
    if (lockCanvas != null) {
        lockCanvas.close();
        localStorage.setItem("ui_lock_status", "unlocked");
    }
}

api.addEventListener("ui_lock", ({ detail }) => {
    console.log(detail);
    if (detail.lock) {
        handleLockScreen();
    }
});

// Close ui_lock listener
api.addEventListener("ui_lock", ({ detail }) => {
    if (!detail.lock) {
        handleUnlockScreen();
    }
});

// Restore ui_lock status on page load
// window.addEventListener("load", () => {
//     const uiLockStatus = localStorage.getItem("ui_lock_status");
//     if (uiLockStatus === "locked") {
//         handleLockScreen();
//     }
// });

(async function checkLockStatus() {
    try {
        const response = await api.fetchApi("/lock");
        const data = await response.json();
        // fixed cannot lock screen
        if (data.lock) {
            handleLockScreen();
        } else {
            handleUnlockScreen();
        }
    } catch (error) {
    }

    // Call the function again after 'lockInterval' seconds
    setTimeout(checkLockStatus, lockInterval);
})();

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
                id: "comfy-settings-dialog-blank",
                parent: document.body,
                style: { width: "33%" , border: 0, padding:0}
            },
            [
                $el("table.comfy-modal-content.comfy-table", [
                    $el(
                        "caption",
                        {
                            id: "black_model_msg",
                            textContent: message
                        },
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

    reset_msg(message){
        document.getElementById("black_model_msg").textContent = message;
    }

    close() {
        this.element.close();
    }
}

// input field dialog
export class ModalEndpointReleaseDialog extends ComfyDialog {

    constructor(app) {
        super();
        this.app = app;
        this.settingsValues = {};
        this.settingsLookup = {};
        this.element = $el(
            "dialog",
            {
                id: "comfy-settings-dialog-release",
                parent: document.body,
                style: { width: "40%" , border: 0, padding:0}
            },
            [
                $el("table.comfy-modal-content.comfy-table", [
                    $el(
                        "caption",
                        { textContent: "Release Environment", style: { border: "0" } },
                    ),
                    $el(
                        "tr",
                        [
                            $el("th", { textContent: "Environment Name", style: { border: "0" } }),
                            $el("td", [
                                $el("input", {
                                    type: "text",
                                    id: "release-input-field",
                                    style: { width: "100%", border: "0" },
                                    value: "",
                                })
                            ])
                        ]
                    ),
                    $el(
                        "caption",
                        { textContent: "Endpoint Config", style: { border: "0" } },
                    ),
                    $el(
                        "tr",
                        [
                            $el("th", { textContent: "Instance Type", style: { border: "0" } }),
                            $el("td", [
                                $el("select", {
                                    id: "select-instance-field",
                                    style: { width: "100%", border: "0" },
                                }, [
                                    $el("option", { value: "ml.g5.2xlarge", textContent: "ml.g5.2xlarge" }),
                                    $el("option", { value: "ml.g5.4xlarge", textContent: "ml.g5.4xlarge" }),
                                    $el("option", { value: "ml.g5.8xlarge", textContent: "ml.g5.8xlarge" }),
                                    $el("option", { value: "ml.g5.12xlarge", textContent: "ml.g5.12xlarge" }),
                                    $el("option", { value: "ml.g5.24xlarge", textContent: "ml.g5.24xlarge" }),
                                    $el("option", { value: "ml.g4dn.4xlarge", textContent: "ml.g4dn.4xlarge" }),
                                    $el("option", { value: "ml.g4dn.8xlarge", textContent: "ml.g4dn.8xlarge" }),
                                    $el("option", { value: "ml.g4dn.12xlarge", textContent: "ml.g4dn.12xlarge" }),
                                    $el("option", { value: "ml.p4d.24xlarge", textContent: "ml.p4d.24xlarge" }),
                                    $el("option", { value: "ml.g6.xlarge", textContent: "ml.g6.xlarge" }),
                                    $el("option", { value: "ml.g6.2xlarge", textContent: "ml.g6.2xlarge" }),
                                    $el("option", { value: "ml.g6.4xlarge", textContent: "ml.g6.4xlarge" }),
                                    $el("option", { value: "ml.g6.8xlarge", textContent: "ml.g6.8xlarge" }),
                                    $el("option", { value: "ml.g6.12xlarge", textContent: "ml.g6.12xlarge" }),
                                    $el("option", { value: "ml.g6.16xlarge", textContent: "ml.g6.16xlarge" }),
                                    $el("option", { value: "ml.g6.24xlarge", textContent: "ml.g6.24xlarge" }),
                                    $el("option", { value: "ml.g6.48xlarge", textContent: "ml.g6.48xlarge" }),
                                ])
                            ]),
                            $el("th", { textContent: "Auto-Scale", style: { border: "0" } }),
                            $el("td", [
                                $el("select", {
                                    id: "select-scale-field",
                                    style: { width: "100%", border: "0" },
                                    onchange: async () => {
                                        const scaleSelectField = document.getElementById("select-scale-field");
                                        const minMaxCountRow = document.getElementById("min-max-count");
                                        minMaxCountRow.hidden = scaleSelectField.value !== 'true';
                                    }
                                }, [
                                    $el("option", { value: true, textContent: "true" }),
                                    $el("option", { value: false, textContent: "false" }),
                                ])
                            ]),
                            $el("th", { textContent: "Init Count", style: { border: "0" } }),
                            $el("td", [
                                $el("input", {
                                    type: "text",
                                    id: "init-count-input-field",
                                    style: { width: "100%", border: "0" },
                                    value: "",
                                })
                            ]),
                        ]
                    ),
                    $el(
                        "tr",
                        {
                            id: "min-max-count",
                            hidden: true
                        },
                        [
                            $el("th", { textContent: "Min-count", style: { border: "0" } }),
                            $el("td", [
                                $el("input", {
                                    type: "text",
                                    id: "min-input-field",
                                    style: { width: "100%", border: "0" },
                                    value: "",
                                })
                            ]),
                            $el("th", { textContent: "Max-Count", style: { border: "0" } }),
                            $el("td", [
                                $el("input", {
                                    type: "text",
                                    id: "max-input-field",
                                    style: { width: "100%", border: "0" },
                                    value: "",
                                })
                            ])
                        ]
                    ),
                    $el(
                        "tr",
                        [
                            $el("td", { colspan: 3, style: { textAlign: "center", border: "0" } }, [
                                $el("button", {
                                    id: "release-ok-button",
                                    textContent: "OK",
                                    style: { marginRight: "10px", width: "60px" },
                                    onclick: async () => {
                                        const workflowNameInputField = document.getElementById("release-input-field");
                                        const initCountInputField = document.getElementById("init-count-input-field");
                                        const instanceTypeSelectField = document.getElementById("select-instance-field");
                                        const scaleSelectField = document.getElementById("select-scale-field");
                                        const minInputField = document.getElementById("min-input-field");
                                        const maxInputField = document.getElementById("max-input-field");
                                        await this.releaseEndpointWorkflow(workflowNameInputField.value, initCountInputField.value, instanceTypeSelectField.value, scaleSelectField.value, minInputField.value, maxInputField.value);
                                    }
                                }),
                                $el("button", {
                                    id: "release-cancel-button",
                                    textContent: "Cancel",
                                    style: { marginRight: "10px", width: "60px" },
                                    onclick: () => this.handleCancelClick(),
                                }),
                                $el("span", {
                                    id: "release-validate-span",
                                    textContent: "",
                                    style: { marginRight: "10px", color: "red" }
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
                [$el("th"), $el("th", { style: { width: "50%" } })]
            )
        );
        this.element.showModal();
    }

    clear(){
        document.getElementById("release-input-field").value = '';
        document.getElementById("init-count-input-field").value = '';
        document.getElementById("select-instance-field").value = '';
        document.getElementById("select-scale-field").value = '';
        document.getElementById("min-input-field").value = '';
        document.getElementById("max-input-field").value = '';
        document.getElementById("release-validate-span").textContent = '';
    }

    async releaseEndpointWorkflow(workflowName, initCount, instanceType, autoScale, minCount, maxCount) {
        // validate names
        if (workflowName.length > 40) {
            document.getElementById("release-validate-span").textContent = 'The environment name cannot exceed 40 characters.';
            return;
        }

        // Check if the input value contains only English letters, numbers, and underscores
        const nameRegex = /^[a-zA-Z0-9_]+$/;
        if (!nameRegex.test(workflowName)) {
            document.getElementById("release-validate-span").textContent = 'The environment name must only contain letters, numbers, and underscores.';
            return;
        }

        // Validate initCount
        if (!initCount || isNaN(initCount) || Number(initCount) < 0) {
            document.getElementById("release-validate-span").textContent = 'Initial count must be a non-negative number.';
            return;
        }

        // Validate minCount and maxCount if autoScale is true
        if (autoScale === true) {
            if (!minCount || isNaN(minCount) || Number(minCount) < 0) {
                document.getElementById("release-validate-span").textContent = 'Min count must be a non-negative number.';
                return;
            }
            if (!maxCount || isNaN(maxCount) || Number(maxCount) < 0) {
                document.getElementById("release-validate-span").textContent = 'Max count must be a non-negative number.';
                return;
            }
        }

        // this.element.close();
        handleLockScreen("Creating...");
        try {
            let payloadJson =await app.graphToPrompt()
            console.log(payloadJson)

            minCount = minCount || "1";
            maxCount = maxCount || "1";

            var target = {
                'name': workflowName,
                'payload_json': payloadJson,
                'initCount': initCount,
                'instanceType': instanceType,
                'autoScale': autoScale,
                'minCount': minCount,
                'maxCount': maxCount,
            };
            const response = await api.fetchApi("/release", {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(target)
            });
            const result = await response.json();
            if (!result.result) {
                handleUnlockScreen();
                document.getElementById("release-validate-span").textContent = result.message;
            } else {
                this.element.close();
            }
        } catch (exception) {
            console.error('Create error:', exception);
            handleUnlockScreen();
            document.getElementById("release-validate-span").textContent = errorMessage;
        }
    }

    handleCancelClick() {
        this.element.close();
    }
}

// var newTemplateName = '';
export class ModalTemplateDialog extends ComfyDialog{
     constructor(app) {
        super();
        this.app = app;
        this.settingsValues = {};
        this.settingsLookup = {};
        this.element = $el(
            "dialog",
            {
                id: "comfy-settings-dialog-temp",
                parent: document.body,
                style: { width: "40%" , border: 0, padding:0}
            },
            [
                $el("table.comfy-modal-content.comfy-table", [
                    $el(
                        "caption",
                        { textContent: "Create Template", style: { border: "0" } },
                    ),
                    $el(
                        "tr",
                        [
                            $el("th", { textContent: "Template Name", style: { border: "0" } }),
                            $el("td", [
                                $el("input", {
                                    type: "text",
                                    id: "input-template_field",
                                    style: { width: "100%", border: "0" },
                                    value: "",
                                })
                            ]),
                            $el("th", { textContent: "Environment Name", style: { border: "0" } }),
                            $el("td", [
                                $el("select", {
                                    id: "select-workflow_field",
                                    style: { width: "100%", border: "0" },
                                })
                            ]),
                        ]
                    ),
                    $el(
                        "tr",
                        [
                            $el("td", { colspan: 3, style: { textAlign: "center", border: "0" } }, [
                                $el("button", {
                                    id: "ok-button",
                                    textContent: "OK",
                                    style: { marginRight: "10px", width: "60px" },
                                    onclick: async () => {
                                        const tempInputField = document.getElementById("input-template_field");
                                        const workflowInputField = document.getElementById("select-workflow_field");
                                        console.log(tempInputField)
                                        console.log(workflowInputField)
                                        await this.createTemplate(tempInputField.value, workflowInputField.value);
                                    }
                                }),
                                $el("button", {
                                    id: "cancel-button",
                                    textContent: "Cancel",
                                    style: { marginRight: "10px", width: "60px" },
                                    onclick: () => this.handleCancelClick(),
                                }),
                                $el("span", {
                                    id: "template-release-validate",
                                    textContent: "",
                                    style: { marginRight: "10px", color: "red" }
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

    clear() {
        document.getElementById("input-template_field").value='';
        document.getElementById("select-workflow_field").value = 'default';
        document.getElementById("template-release-validate").textContent = '';

    }

    populateWorkflowSelectField() {
        api.fetchApi("/workflows", {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
        })
        .then(response => response.json())
        .then(data => {
            if (data.data && Array.isArray(data.data.workflows)) {
                const workflowSelectField = document.getElementById("select-workflow_field");
                workflowSelectField.innerHTML = '';
                data.data.workflows.forEach(workflow => {
                    if (workflow.status === 'Enabled') {
                        const option = document.createElement('option');
                        option.value = workflow.name;
                        option.textContent = `${workflow.name}(${workflow.size})`;
                        workflowSelectField.appendChild(option);
                    }
                });
            } else {
                console.error('Failed to fetch workflow names:', data.message);
            }
        })
        .catch(exception => {
            console.error('Error fetching workflow names:', exception);
        });
    }


    async createTemplate(templateName, workflowName) {
        // validate names
        if (templateName.length > 40) {
            document.getElementById("template-release-validate").textContent = 'The template name cannot exceed 40 characters.';
            return;
        }

        // Check if the input value contains only English letters, numbers, and underscores
        const nameRegex = /^[a-zA-Z0-9_]+$/;
        if (!nameRegex.test(templateName)) {
            document.getElementById("template-release-validate").textContent = 'The template name must only contain letters, numbers, and underscores.';
            return;
        }

        // this.element.close();
        handleLockScreen("Creating...");
        try {
            let payloadJson =await app.graphToPrompt()
            if (typeof payloadJson === 'object') {
                payloadJson = JSON.stringify(payloadJson);
            }
            console.log(payloadJson)
            var target = {
                'name': templateName,
                'payload': payloadJson,
                'workflow': workflowName
            };
            const response = await api.fetchApi("/schemas", {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(target)
            });
            const result = await response.json();
            if (!result.result) {
                handleUnlockScreen();
                document.getElementById("template-release-validate").textContent = result.message;
            } else {
                this.element.close();
            }
        } catch (exception) {
            console.error('Create error:', exception);
            handleUnlockScreen();
            document.getElementById("template-release-validate").textContent = errorMessage;
        }
    }

    handleCancelClick() {
        this.element.close();
    }
}

export class ModalEditTemplateDialog extends ComfyDialog{
    constructor(app, selectedItem) {
        super();
        this.app = app;
        this.settingsValues = {};
        this.settingsLookup = {};
        this.selectedItem = selectedItem;
        this.element = $el(
            "dialog",
            {
                id: "comfy-settings-dialog-edit",
                parent: document.body,
                style: { width: "50%" , border: 0, padding:0}
            },
            [
                $el("table.comfy-modal-content.comfy-table", [
                    $el(
                        "caption",
                        { textContent: "Edit Template", style: { border: "0" } },
                    ),
                    $el(
                        "tr",
                        [
                            $el("th", { textContent: "Template Name", style: { border: "0" } }),
                            $el("td", [
                                $el("input", {
                                    type: "text",
                                    id: "edit-template_field",
                                    style: { width: "100%", border: "0" },
                                    value: selectedItem.firstChild.firstChild.textContent,
                                    disabled: true,
                                })
                            ]),
                            $el("th", { textContent: "Workflow Name", style: { border: "0" } }),
                            $el("td", [
                                $el("select", {
                                    id: "edit-workflow_field",
                                    style: { width: "100%", border: "0" },
                                })
                            ]),
                        ]
                    ),
                    $el(
                        "tr",
                        [
                            $el("td", { colspan: 3, style: { textAlign: "center", border: "0" } }, [
                                $el("button", {
                                    id: "edit-ok-button",
                                    textContent: "OK",
                                    style: { marginRight: "10px", width: "60px" },
                                    onclick: async () => {
                                        const tempEditField = document.getElementById("edit-template_field");
                                        const workflowEditField = document.getElementById("edit-workflow_field");
                                        console.log(tempEditField)
                                        console.log(workflowEditField)
                                        await this.editTemplate(tempEditField.value, workflowEditField.value);
                                    }
                                }),
                                $el("button", {
                                    id: "edit-cancel-button",
                                    textContent: "Cancel",
                                    style: { marginRight: "10px", width: "60px" },
                                    onclick: () => this.handleCancelClick(),
                                }),
                                $el("span", {
                                    id: "edit-release-validate",
                                    textContent: "",
                                    style: { marginRight: "10px", color: "red" }
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

    clear(selectedItem) {
        document.getElementById("edit-template_field").value = selectedItem.firstChild.firstChild.textContent;
        document.getElementById("edit-workflow_field").value = 'default';
        document.getElementById("edit-release-validate").textContent = '';
    }

    populateWorkflowSelectField() {
        api.fetchApi("/workflows", {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
        })
        .then(response => response.json())
        .then(data => {
            if (data.data && Array.isArray(data.data.workflows)) {
                const workflowSelectField = document.getElementById("edit-workflow_field");
                workflowSelectField.innerHTML = '';
                data.data.workflows.forEach(workflow => {
                    if (workflow.status === 'Enabled') {
                        const option = document.createElement('option');
                        option.value = workflow.name;
                        option.textContent = `${workflow.name}(${workflow.size})`;
                        workflowSelectField.appendChild(option);
                    }
                });
            } else {
                console.error('Failed to fetch workflow names:', data.message);
            }
        })
        .catch(exception => {
            console.error('Error fetching workflow names:', exception);
        });
    }


    async editTemplate(templateName, workflowName) {

        // this.element.close();
        handleLockScreen("Updating...");
        try {
            let payloadJson =await app.graphToPrompt()
            if (typeof payloadJson === 'object') {
                payloadJson = JSON.stringify(payloadJson);
            }
            console.log(payloadJson)
            var target = {
                'name': templateName,
                'payload': payloadJson,
                'workflow': workflowName
            };
            const response = await api.fetchApi("/schemas", {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(target)
            });
            const result = await response.json();
            if (!result.result) {
                handleUnlockScreen();
                document.getElementById("edit-release-validate").textContent = result.message;
            } else {
                this.element.close();
            }
        } catch (exception) {
            console.error('Update error:', exception);
            handleUnlockScreen();
            document.getElementById("edit-release-validate").textContent = errorMessage;
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
                id: "comfy-settings-dialog-confirm",
                parent: document.body,
                style: { width: "33%" , border: 0, padding:0}
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
                            $el("td", { colspan: 2, style: { textAlign: "center", border: "0" } }, [
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
                id: "comfy-settings-dialog-msg",
                parent: document.body,
                style: { width: "33%" , border: 0, padding:0}
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
