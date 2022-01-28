"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    Object.defineProperty(o, k2, { enumerable: true, get: function() { return m[k]; } });
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.multiStepInput = void 0;
const vscode_1 = require("vscode");
const path = __importStar(require("path"));
const vscode = __importStar(require("vscode"));
const utils_1 = require("./utils");
const mainToolPath = path.join(path.dirname(__dirname), "testing_tool", "my_tool");
function multiStepInput(func, codeFile, linenb, inputslst, root, workspace, userInput, logging) {
    return __awaiter(this, void 0, void 0, function* () {
        // Selection of input types
        const inputtypes = ['string', 'integer', 'float', 'boolean', 'other']
            .map(label => ({ label }));
        const yesno = ['yes', 'no'].map(label => ({ label }));
        // Launch the multi step input by running this function
        function collectInputs() {
            return __awaiter(this, void 0, void 0, function* () {
                const state = { types: '', params: '' };
                yield MultiStepInput.run(input => pickType(input, state, 1));
                return state;
            });
        }
        // Function creates a QuickPick, where user chooses type of parameter.
        function pickType(input, state, index) {
            return __awaiter(this, void 0, void 0, function* () {
                const pick = yield input.showQuickPick({
                    title: 'function:  ' + func + ', parameter: ' + inputslst[index - 1],
                    placeholder: 'Pick a type for input ' + index + ': ' + inputslst[index - 1],
                    items: inputtypes,
                    shouldResume: shouldResume
                });
                // This will launch an Input Box where the user can input their own type.
                if (pick.label === 'other') {
                    return (input) => inputOtherType(input, state, index, '');
                }
                // This will prompt the multi step input to go onto the next parameter.
                else {
                    state.types += ', ' + pick.label;
                    if (inputslst.length > 1) {
                        return (input) => inputAPIParam(input, state, index);
                    }
                    else {
                        state.params += ', ' + inputslst[index - 1];
                    }
                }
            });
        }
        // Function creates a InputBox, where user inputs their own type.
        function inputOtherType(input, state, index, placeholder) {
            return __awaiter(this, void 0, void 0, function* () {
                placeholder = yield input.showInputBox({
                    title: func + ' inputs',
                    value: typeof placeholder === 'string' ? placeholder : '',
                    prompt: 'Choose a type for input ' + index,
                    validate: validateNameIsUnique,
                    shouldResume: shouldResume
                });
                state.types += ', ' + placeholder;
                if (inputslst.length > 1) {
                    return (input) => inputAPIParam(input, state, index);
                }
                else {
                    state.params += ', ' + inputslst[index - 1];
                }
            });
        }
        function inputAPIParam(input, state, index) {
            return __awaiter(this, void 0, void 0, function* () {
                const pick = yield input.showQuickPick({
                    title: 'In the function ' + func + ' is ' + inputslst[index - 1] + ' used in the ML API?',
                    placeholder: 'Is ' + inputslst[index - 1] + ' used in the ML API',
                    items: yesno,
                    shouldResume: shouldResume
                });
                if (pick.label === 'yes') {
                    state.params += ', ' + inputslst[index - 1];
                }
                if (index < inputslst.length) {
                    return (input) => pickType(input, state, index + 1);
                }
            });
        }
        function shouldResume() {
            // Could show a notification with the option to resume.
            return new Promise((resolve, reject) => {
                // noop
            });
        }
        function validateNameIsUnique(name) {
            return __awaiter(this, void 0, void 0, function* () {
                // ...validate...
                yield new Promise(resolve => setTimeout(resolve, 1000));
                return name === 'vscode' ? 'Name not unique' : undefined;
            });
        }
        let typesinput = " ";
        let params = " ";
        // launch multi step input
        if (inputslst.length > 0) {
            const t = yield collectInputs();
            if (t.types !== undefined && t.params !== undefined) {
                typesinput = typesinput.substring(1).concat(t.types);
                params = params.substring(1).concat(t.params);
            }
        }
        // create json file with input type information
        // NOTE: user input is not needed because this python file can be easily executed in any env
        let cmd = `cd ${root}; python type_output.py -f '${func}' -t '${typesinput.substring(1)}' -d '${workspace}' -n '${linenb}' -cf '${codeFile}' -p '${params.substring(1)}'`;
        utils_1.executeSync(cmd);
        vscode_1.window.showInformationMessage(`Your input has been collected! Now running our testing tool. You can click the button below to view progress in logging`, 'Log Messages').then(selection => {
            if (selection === 'Log Messages') {
                logging.show();
            }
        });
        const inputJson = path.join(workspace, '/.vscode/tool_json_files/user_input.json');
        const outputJson = path.join(workspace, '/.vscode/tool_json_files/bugs.json');
        const logsJson = path.join(workspace, '/.vscode/tool_json_files/logs.txt');
        cmd = `cd ${mainToolPath}; ${userInput} python3.8 -u all_wrap_up.py --input_json ${inputJson} --output_json ${outputJson} --log_file ${logsJson}`;
        utils_1.execute(cmd, ((value) => {
            if (value !== 0) {
                vscode_1.window.showErrorMessage(`There was an error in finding failures, please check that you submitted the correct inputs and that you don't have simple syntax errors in your code. Click the button below to be redirected to the input file we use to find failures. Make sure all the information in this file is correct. You can also inspect our tool output here`, 'Input file', 'Log Messages')
                    .then(selection => {
                    if (selection === 'Input file') {
                        vscode.workspace.openTextDocument(inputJson).then(iDoc => {
                            vscode.window.showTextDocument(iDoc).then(editor => { });
                        });
                    }
                    else if (selection === 'Log Messages') {
                        logging.show();
                    }
                });
            }
        }), logging);
    });
}
exports.multiStepInput = multiStepInput;
// MultiStepInput
class InputFlowAction {
}
InputFlowAction.back = new InputFlowAction();
InputFlowAction.cancel = new InputFlowAction();
InputFlowAction.resume = new InputFlowAction();
class MultiStepInput {
    constructor() {
        this.steps = [];
    }
    static run(start) {
        return __awaiter(this, void 0, void 0, function* () {
            const input = new MultiStepInput();
            return input.stepThrough(start);
        });
    }
    stepThrough(start) {
        return __awaiter(this, void 0, void 0, function* () {
            let step = start;
            while (step) {
                this.steps.push(step);
                if (this.current) {
                    this.current.enabled = false;
                    this.current.busy = true;
                }
                try {
                    step = yield step(this);
                }
                catch (err) {
                    if (err === InputFlowAction.back) {
                        this.steps.pop();
                        step = this.steps.pop();
                    }
                    else if (err === InputFlowAction.resume) {
                        step = this.steps.pop();
                    }
                    else if (err === InputFlowAction.cancel) {
                        step = undefined;
                    }
                    else {
                        throw err;
                    }
                }
            }
            if (this.current) {
                this.current.dispose();
            }
        });
    }
    showQuickPick({ title, items, activeItem, placeholder, buttons, shouldResume }) {
        return __awaiter(this, void 0, void 0, function* () {
            const disposables = [];
            try {
                return yield new Promise((resolve, reject) => {
                    const input = vscode_1.window.createQuickPick();
                    input.title = title;
                    input.placeholder = placeholder;
                    input.items = items;
                    if (activeItem) {
                        input.activeItems = [activeItem];
                    }
                    input.buttons = [
                        ...(this.steps.length > 1 ? [vscode_1.QuickInputButtons.Back] : []),
                        ...(buttons || [])
                    ];
                    disposables.push(input.onDidTriggerButton(item => {
                        if (item === vscode_1.QuickInputButtons.Back) {
                            reject(InputFlowAction.back);
                        }
                        else {
                            resolve(item);
                        }
                    }), input.onDidChangeSelection(items => resolve(items[0])), input.onDidHide(() => {
                        (() => __awaiter(this, void 0, void 0, function* () {
                            reject(shouldResume && (yield shouldResume()) ? InputFlowAction.resume : InputFlowAction.cancel);
                        }))()
                            .catch(reject);
                    }));
                    if (this.current) {
                        this.current.dispose();
                    }
                    this.current = input;
                    this.current.show();
                });
            }
            finally {
                disposables.forEach(d => d.dispose());
            }
        });
    }
    showInputBox({ title, value, prompt, validate, buttons, shouldResume }) {
        return __awaiter(this, void 0, void 0, function* () {
            const disposables = [];
            try {
                return yield new Promise((resolve, reject) => {
                    const input = vscode_1.window.createInputBox();
                    input.title = title;
                    input.value = value || '';
                    input.prompt = prompt;
                    input.buttons = [
                        ...(this.steps.length > 1 ? [vscode_1.QuickInputButtons.Back] : []),
                        ...(buttons || [])
                    ];
                    let validating = validate('');
                    disposables.push(input.onDidTriggerButton(item => {
                        if (item === vscode_1.QuickInputButtons.Back) {
                            reject(InputFlowAction.back);
                        }
                        else {
                            resolve(item);
                        }
                    }), input.onDidAccept(() => __awaiter(this, void 0, void 0, function* () {
                        const value = input.value;
                        input.enabled = false;
                        input.busy = true;
                        if (!(yield validate(value))) {
                            resolve(value);
                        }
                        input.enabled = true;
                        input.busy = false;
                    })), input.onDidChangeValue((text) => __awaiter(this, void 0, void 0, function* () {
                        const current = validate(text);
                        validating = current;
                        const validationMessage = yield current;
                        if (current === validating) {
                            input.validationMessage = validationMessage;
                        }
                    })), input.onDidHide(() => {
                        (() => __awaiter(this, void 0, void 0, function* () {
                            reject(shouldResume && (yield shouldResume()) ? InputFlowAction.resume : InputFlowAction.cancel);
                        }))()
                            .catch(reject);
                    }));
                    if (this.current) {
                        this.current.dispose();
                    }
                    this.current = input;
                    this.current.show();
                });
            }
            finally {
                disposables.forEach(d => d.dispose());
            }
        });
    }
}
//# sourceMappingURL=userInput.js.map