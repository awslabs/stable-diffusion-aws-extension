import {app} from "../../scripts/app.js";
import {$el} from "../../scripts/ui.js";
import {api} from "../../scripts/api.js"

const id = "Comfy.ComfyRestartService";

async function restartEc2() {
    await api.fetchApi('/reboot', {
        method: 'GET'
    }).then(response => {
        return response.json()
    }).then(response => {
        console.log(response);
        alert(response.message);
        if (response.reload_timeout) {
            setTimeout(() => {
                location.reload();
            }, response.reload_timeout);
        }
    }).catch(error => {
        alert("Error: " + error.message);
        console.error('Error:', error);
    });
}

async function restartService() {
    await api.fetchApi('/restart', {
        method: 'GET'
    }).then(response => {
        return response.json()
    }).then(response => {
        console.log(response);
        alert(response.message);
        if (response.reload_timeout) {
            setTimeout(() => {
                location.reload();
            }, response.reload_timeout);
        }
    }).catch(error => {
        alert("Error: " + error.message);
        console.error('Error:', error);
    });
}

// const ctxMenu = LiteGraph.ContextMenu;
app.registerExtension({
    name: id,
    addCustomNodeDefs(node_defs) {

        app.ui.settings.addSetting({
            id,
            name: "Comfy Restart",
            type: (name, setter, value) => {

                return $el("tr", [

                    $el("td", [
                        $el("label", {
                            for: id.replaceAll(".", "-"),
                            textContent: "Comfy Restart",
                        }),
                    ]),

                    $el("td", [

                        $el("div", {
                            style: {
                                display: "grid",
                                gap: "4px",
                                gridAutoFlow: "column",
                            },
                        }, [
                            $el("input", {
                                type: "button",
                                value: "Restart Comfy",
                                onclick: async () => {
                                    if (confirm("Do you confirm to restart the comfy service?")) {
                                        await restartService();
                                    }
                                }
                            }),
                            $el("input", {
                                type: "button",
                                value: "Reboot EC2",
                                onclick: async () => {
                                    if (confirm("Do you confirm to reboot the EC2?")) {
                                        await restartEc2();
                                    }
                                }
                            }),
                        ]),
                    ]),
                ])
            },

        });
    },
});
