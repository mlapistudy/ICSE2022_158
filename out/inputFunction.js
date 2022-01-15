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
exports.inputmultiStepInput = void 0;
const vscode_1 = require("vscode");
const path = __importStar(require("path"));
const vscode = __importStar(require("vscode"));
const utils_1 = require("./utils");
const mainToolPath = path.join(path.dirname(path.dirname(__dirname)), "testing_tool", "my_tool");
function inputmultiStepInput(root, workspace, userInput, logging) {
    return __awaiter(this, void 0, void 0, function* () {
        // Launch the multi step input by running this function
        function collectInputs() {
            return __awaiter(this, void 0, void 0, function* () {
                const state = {};
                yield MultiStepInput.run(input => inputFuncName(input, state, ''));
                return state;
            });
        }
        // Function creates a InputBox, where user inputs their own type.
        function inputFuncName(input, state, placeholder) {
            return __awaiter(this, void 0, void 0, function* () {
                placeholder = yield input.showInputBox({
                    title: 'Input information for a function',
                    value: typeof placeholder === 'string' ? placeholder : '',
                    prompt: 'Write in function name',
                    validate: validateNameIsUnique,
                    shouldResume: shouldResume
                });
                state.func_name = placeholder;
                return (input) => inputCodeFile(input, state, '');
            });
        }
        function inputCodeFile(input, state, placeholder) {
            return __awaiter(this, void 0, void 0, function* () {
                placeholder = yield input.showInputBox({
                    title: 'Input information for a function',
                    value: typeof placeholder === 'string' ? placeholder : '',
                    prompt: 'Input directory where function code is located, e.g. /Users/janedoe/downloads/code/file.py',
                    validate: validateNameIsUnique,
                    shouldResume: shouldResume
                });
                state.code_file = placeholder;
                return (input) => inputFuncDefLine(input, state, '');
            });
        }
        function inputFuncDefLine(input, state, placeholder) {
            return __awaiter(this, void 0, void 0, function* () {
                placeholder = yield input.showInputBox({
                    title: 'Input information for a function',
                    value: typeof placeholder === 'string' ? placeholder : '',
                    prompt: 'Input line number of the function name',
                    validate: validateNameIsUnique,
                    shouldResume: shouldResume
                });
                state.func_def_line = placeholder;
                return (input) => inputInputTypes(input, state, '');
            });
        }
        function inputInputTypes(input, state, placeholder) {
            return __awaiter(this, void 0, void 0, function* () {
                placeholder = yield input.showInputBox({
                    title: 'Input information for a function',
                    value: typeof placeholder === 'string' ? placeholder : '',
                    prompt: 'Input the types of the function parameters in the format type1, type2, etc.',
                    validate: validateNameIsUnique,
                    shouldResume: shouldResume
                });
                state.input_types = placeholder;
                return (input) => inputAPIParams(input, state, '');
            });
        }
        function inputAPIParams(input, state, placeholder) {
            return __awaiter(this, void 0, void 0, function* () {
                placeholder = yield input.showInputBox({
                    title: 'Input information for a function',
                    value: typeof placeholder === 'string' ? placeholder : '',
                    prompt: 'Input parameters used in API in the format input1, input2, etc.',
                    validate: validateNameIsUnique,
                    shouldResume: shouldResume
                });
                state.api_params = placeholder;
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
        const state = yield collectInputs();
        // create json file with input type information
        // NOTE: user input is not needed because this python file can be easily executed in any env
        let cmd = `cd ${root}; python type_output.py -f '${state.func_name}' -t '${state.input_types}' -d '${workspace}' -n '${state.func_def_line}' -cf '${state.code_file}' -p '${state.api_params}'`;
        utils_1.executeSync(cmd);
        vscode_1.window.showInformationMessage(`Your input has been collected! Now running our testing tool. You can click the button below to view progress in logging`, 'Log Messages').then(selection => {
            if (selection === 'Log Messages') {
                logging.show();
            }
        });
        const mainToolPath = path.join(path.dirname(path.dirname(__dirname)), "testing_tool", "my_tool");
        const exportPaths = "export GOOGLE_APPLICATION_CREDENTIALS='/Users/cwan/Desktop/API_paper/ML-API-7a2899da539f.json'; export PYTHONPATH=/usr/local/share/pyshared/;"; //"export GOOGLE_APPLICATION_CREDENTIALS='/path/to/your/google/credential.json'; export PYTHONPATH=/usr/local/share/pyshared/;";
        const inputJson = path.join(workspace, '/.vscode/tool_json_files/user_input.json');
        const outputJson = path.join(workspace, '/.vscode/tool_json_files/bugs.json');
        const logsJson = path.join(workspace, '/.vscode/tool_json_files/logs.txt');
        cmd = `cd ${mainToolPath}; ${userInput} ${exportPaths} python3.8 -u all_wrap_up.py --input_json ${inputJson} --output_json ${outputJson} --log_file ${logsJson}`;
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
exports.inputmultiStepInput = inputmultiStepInput;
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
//# sourceMappingURL=inputFunction.js.map