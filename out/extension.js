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
Object.defineProperty(exports, "__esModule", { value: true });
exports.deactivate = exports.activate = void 0;
// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
const vscode = __importStar(require("vscode"));
const vscode_1 = require("vscode");
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const treeView_1 = require("./treeView");
const treeViewError_1 = require("./treeViewError");
const highlight_1 = require("./highlight");
const userInput_1 = require("./userInput");
const inputFunction_1 = require("./inputFunction");
const utils_1 = require("./utils");
// this method is called when your extension is activated
// your extension is activated the very first time the command is executed
function activate(context) {
    // Create logging window
    let logging = vscode_1.window.createOutputChannel("ML API Testing");
    // Use the console to output diagnostic information (console.log) and errors (console.error)
    // This line of code will only be executed once when your extension is activated
    console.log('Congratulations, your extension "ML API Testing" is now active!');
    logging.appendLine('Congratulations, your extension "ML API Testing" is now active!');
    let config = vscode.workspace.getConfiguration('mlapi-testing');
    let userInput = config.setUpEnvironmentAndApplicationPrerequisites;
    console.log("Current working directory: ", __dirname);
    console.log("Filepath: ", __filename);
    console.log("userInput: ", userInput);
    let currDir = path.join(__dirname.substring(0, __dirname.length - 4), "src");
    if (vscode.workspace.rootPath) {
        fromWorkspace(vscode.workspace.rootPath, currDir, userInput, context, logging);
    }
    vscode.workspace.onDidChangeWorkspaceFolders(event => {
        console.log("onDidChangeWorkspaceFolders occured");
        if (vscode.workspace.rootPath) {
            fromWorkspace(vscode.workspace.rootPath, currDir, userInput, context, logging);
        }
        else {
            console.log("workspaceFolders is still undefined, this should not happen!");
        }
    });
}
exports.activate = activate;
function getTestableFunction(rootPath, currDir, userInput, testableFunctionsProvider, logging) {
    // get the testable function output from AST static analysis
    utils_1.execute(`cd ${currDir} && ${userInput} python3.8 -u function_trace.py -w ${rootPath}`, () => { testableFunctionsProvider.refresh(); }, logging);
}
// when workspace is opened or when workspace changed, evoke this
function fromWorkspace(rootPath, currDir, userInput, context, logging) {
    console.log(`rootPath given is ${rootPath}`);
    let toolFilesFolder = path.join(rootPath, '/.vscode/tool_json_files/');
    const packageJsonPath = path.join(rootPath, '/.vscode/tool_json_files/testable_functions.json');
    const bugsJsonPath = path.join(rootPath, '/.vscode/tool_json_files/bugs.json');
    // removes the folder and creates it again to make sure everything is cleaned up
    utils_1.executeSync(`if [ -d ${toolFilesFolder} ]; then rm -rf ${toolFilesFolder}; fi; mkdir -p ${toolFilesFolder}; echo "[]" > ${bugsJsonPath}; echo '{"children": []}' > ${packageJsonPath}`, logging);
    // testable function registration
    let testableFunction = new treeView_1.TestableFunctionsProvider(packageJsonPath);
    vscode.window.registerTreeDataProvider('mlapitesting', testableFunction);
    // bugs view and output highlighter. Note that the input json files for these
    // two are set to empty at start to not invoke any potential problems
    // they have respective `refresh` functionalities implemented to be called
    let bugProvider = new treeViewError_1.BugsProvider(bugsJsonPath);
    let hover = new highlight_1.OutputHighlight(bugsJsonPath, rootPath, logging);
    vscode.window.registerTreeDataProvider('mlapiBugsVis', bugProvider);
    context.subscriptions.push(vscode.commands.registerCommand('mlapitesting.refreshErrorEntry', () => bugProvider.refresh()));
    // Watching changes in the bugs.json file so that we can update the bugs treeView
    fs.watch(bugsJsonPath, function (event, filename) {
        console.log('event is: ' + event);
        if (filename) {
            console.log('filename provided: ' + filename);
        }
        else {
            console.log('filename not provided');
        }
        logging.appendLine(`Refreshing failures treeview output because ${filename} changes, hold on for a bit!`);
        bugProvider.refresh();
        hover.refresh();
        hover.updateJsonDecorations();
        logging.appendLine("Finished refreshing failures view. New failures should be visible in the 'Function with failures' view!");
    });
    // Refreshing the testable functions treeview when a python file changes
    // The reason why we are using both vscode and fs's API is because the VSCode
    // API seems to detect many changes in the workspace and fails to trigger
    // the commented out else if branch
    vscode.workspace.onDidChangeTextDocument(function (TextDocumentChangeEvent) {
        let filename = TextDocumentChangeEvent.document.fileName;
        if (filename.includes(".py")) {
            logging.appendLine(`refreshing testable function treeview because ${filename} changes`);
            utils_1.executeSync(`echo '{"children": []}' > ${packageJsonPath}`, logging);
            testableFunction.refresh();
        }
        // else if (filename.includes("/.vscode/tool_json_files/bugs.json")) {
        // 	bugProvider.refresh();
        // 	hover.refresh(); hover.updateJsonDecorations();
        // 	logging.appendLine("Process completed.");
        // }
    });
    vscode.commands.registerCommand('mlapitesting.getTestableFunction', () => {
        logging.appendLine("Getting testable functions...");
        console.log("Getting testable functions...");
        getTestableFunction(rootPath, currDir, userInput, testableFunction, logging);
    });
    // Show logging window
    context.subscriptions.push(vscode.commands.registerCommand('mlapitesting.logging', () => {
        logging.show();
    }));
    context.subscriptions.push(vscode.commands.registerCommand('mlapitesting.test', (arg1) => {
        console.log("Testing using the TEST THIS FUNCTION button");
        logging.appendLine("Testing using the TEST THIS FUNCTION button");
        userInput_1.multiStepInput(arg1.label, arg1.filePath, arg1.lineNb, arg1.args, currDir, rootPath, userInput, logging);
    }));
    context.subscriptions.push(vscode.commands.registerCommand('mlapitesting.inputfunction', () => {
        console.log("Testing using the INPUT YOUR OWN FUNCTION");
        logging.appendLine("Testing using the INPUT YOUR OWN FUNCTION");
        inputFunction_1.inputmultiStepInput(currDir, rootPath, userInput, logging);
    }));
    context.subscriptions.push(vscode.workspace.onDidChangeConfiguration(event => {
        console.log("onDidChangeConfiguration occurs");
        logging.appendLine("Changed configuration in ML API Testing settings");
        if (event.affectsConfiguration('mlapi-testing.setUpEnvironmentAndApplicationPrerequisites')) {
            let config = vscode.workspace.getConfiguration('mlapi-testing');
            let userInput = config.setUpEnvironmentAndApplicationPrerequisites;
            if (userInput !== '') {
                // TODO: change this to the correct refreshing method
                getTestableFunction(rootPath, currDir, userInput, testableFunction, logging);
            }
        }
    }));
    // Register different commands
    context.subscriptions.push(vscode.commands.registerCommand('mlapitesting.highlight', () => {
        hover.refresh();
        hover.updateJsonDecorations();
    }));
    context.subscriptions.push(vscode.commands.registerCommand('mlapitesting.unhighlight', () => {
        hover.refresh();
        hover.unhighlightAll();
    }));
}
// this method is called when your extension is deactivated
function deactivate() { }
exports.deactivate = deactivate;
//# sourceMappingURL=extension.js.map