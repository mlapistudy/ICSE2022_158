'use strict';
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
exports.OutputHighlight = void 0;
const child_process_1 = require("child_process");
const path = __importStar(require("path"));
const fs = require('fs');
const vscode_1 = require("vscode");
// Stores the handle (actually type Disposable but has to set to any for NULL compatibility)
// returned by registerring to an event
let changeHandle = null;
// TODO: Figure out better decoration types with support for different themes
const accuracyHighlight = vscode_1.window.createTextEditorDecorationType({
    // isWholeLine: false,
    // backgroundColor: new ThemeColor('red'),
    borderWidth: `0 0 3px 0`,
    borderStyle: `dotted`,
    borderColor: `red`
    // color: new ThemeColor("#fc8403")
});
const deadcodeHighlight = vscode_1.window.createTextEditorDecorationType({
    borderWidth: `0 0 3px 0`,
    borderStyle: `dotted`,
    borderColor: `blue`
});
const crashHighlight = vscode_1.window.createTextEditorDecorationType({
    borderWidth: `0 0 3px 0`,
    borderStyle: `dotted`,
    borderColor: `yellow`
});
// Hover implementation
class OutputHighlight {
    constructor(jsonFile, workspace, logging) {
        this.jsonFile = jsonFile;
        this.mainJson = require(`${jsonFile}`);
        this.workspace = workspace;
        this.logging = logging;
        this.currentTextIndex = 0;
        console.log(`Executed MLAPIHoverProvider constructor, JSON file set to ${jsonFile}`);
    }
    refresh() {
        console.log(`refresh for Output Highlight activated, JSON file set to ${this.jsonFile}`);
        delete require.cache[require.resolve(`${this.jsonFile}`)];
        this.mainJson = require(`${this.jsonFile}`);
    }
    positionWithinLine(position, line) {
        return line.includes(position.line);
    }
    ;
    // Renders the string to be displayed on hover
    renderDisplayString(bug_type, description, fix_suggestion, test_input, workspace) {
        let res = new vscode_1.MarkdownString();
        res.appendMarkdown(`**Failure Type**: ${bug_type} Failure\n\n***\n\n`);
        res.appendMarkdown(`**Description**: ${description}\n\n***\n\n`);
        if (fix_suggestion !== undefined) {
            res.appendMarkdown(`**Fix Suggestion**:\n\n${fix_suggestion}\n\n***\n\n`);
        }
        if (test_input !== undefined) {
            res.appendMarkdown("**Failure Triggering Input**:\n\n");
            // each test_input is a key-value pair
            test_input.forEach((element, index) => {
                this.currentTextIndex++;
                Object.entries(element).forEach(([key, value]) => {
                    // console.log(`Number ${this.currentTextIndex} is key, value pair is ${key}, ${value}`);
                    // Matching value with filepath in RegEx
                    if (fs.existsSync(value)) {
                        console.log(`string ${value} as a file exists`);
                        res.appendMarkdown(`[Click here to see image input ${this.currentTextIndex}](${value})  \n`);
                    }
                    else {
                        const textInput = path.join(workspace, `/.vscode/tool_json_files/textinput_${this.currentTextIndex}.txt`);
                        value = value.replace(/"/g, '\\"');
                        value = value.replace(/'/g, "\\'");
                        value = value.replace(/\?/g, "\\?");
                        value = value.replace(/\^/g, "\\^");
                        value = value.replace(/\//g, "\\/");
                        value = value.replace(/\&/g, "\\&");
                        value = value.replace(/\;/g, "\\;");
                        value = value.replace(/\(/g, "\\(");
                        value = value.replace(/\)/g, "\\)");
                        value = value.replace(/\!/g, "\\!");
                        value = value.replace(/\#/g, "\\#");
                        value = value.replace(/\>/g, "\\>");
                        value = value.replace(/\</g, "\\<");
                        value = value.replace(/\*/g, "\\*");
                        value = value.replace(/\`/g, "\\`");
                        value = value.replace(/\~/g, "\\~");
                        value = value.replace(/\|/g, "\\|");
                        value = value.replace(/\$/g, "\\$");
                        value = value.replace(/\[/g, "\\[");
                        value = value.replace(/\]/g, "\\]");
                        value = value.replace(/\{/g, "\\{");
                        value = value.replace(/\}/g, "\\}");
                        //this.logging.append(value);
                        console.log(`executing command: echo ${value} > ${textInput}`);
                        child_process_1.execSync(`echo ${value} > ${textInput}`);
                        res.appendMarkdown(`[Click here to see text input ${this.currentTextIndex}](${textInput})  \n`);
                    }
                });
            });
            res.appendMarkdown("\n\n");
        }
        res.appendMarkdown("*source: ML API Testing Plugin*");
        return res;
    }
    // Given a file and editor, congregate which lines need to update
    updateDecorations(fileToUpdate, updateLines, editor, hoverMessage) {
        let decorationList = [];
        // console.log(`editor pointing to ${editor.document.fileName}`);
        // console.log(`fileToUpdate from JSON pointing to ${fileToUpdate}`);
        // Check if the editor's filename corresponds to the desired file to be updated
        if (editor.document.fileName === fileToUpdate) {
            updateLines.forEach((updateLine) => {
                updateLine -= 1;
                let endLineText = editor.document.lineAt(updateLine);
                // Because the Range operator expects character information, 0 and the Math.max are character information
                decorationList.push({ range: new vscode_1.Range(updateLine, 0, updateLine, Math.max(endLineText.text.length, 0)), hoverMessage: hoverMessage });
                console.log(`underlining line ${updateLine} upto ${Math.max(endLineText.text.length, 0)}`);
                //this.logging.appendLIne(`underlining line ${updateLine} upto ${Math.max(endLineText.text.length, 0)}`);
            });
        }
        return decorationList;
    }
    // Currently unused
    retrieveInJson(position, codeFile) {
        var res = [];
        this.mainJson.forEach((element) => {
            // NOTE: we might need better file path comparisons for portability
            // console.log(`element.code_file is ${element.code_file}`);
            // console.log(`codeFile is ${codeFile}`);
            if (element.code_file === codeFile) {
                // console.log("Executing positionWithinLine");
                if (element.lines_of_code.includes(position.line)) {
                    // console.log("positionWithinLine returns true");
                    res.push(this.renderDisplayString(element.bug_type, element.description, element.fix_suggestion, element.test_input, this.workspace));
                }
            }
        });
        return res;
    }
    // function to be registered with a command
    // TODO for future support: after our tool finishes, initiate this
    updateJsonDecorations() {
        // Iterate through all bug types first
        ["Crash", "Accuracy", "Dead Code"].forEach((bug_type) => {
            // Iterate through all text editors
            // Assemble a decoration list for each text editor + each bug type
            // Each bug type corresponds to the `bug_level` iteration, i.e., the top level of json file
            // The reason for this is we can only call editor.setDecorations with one style once
            // If we call it with the same style twice, then the second one replaces the effect of the first one
            vscode_1.window.visibleTextEditors.forEach((editor) => {
                this.currentTextIndex = 0;
                var self = this;
                this.mainJson.forEach(function (bug_level) {
                    let decorationList = [];
                    bug_level.bugs.forEach(function (element) {
                        // if (bug_level.bug_type === element.bug_type) {
                        decorationList = decorationList.concat(self.updateDecorations(element.code_file, element.lines_of_code, editor, self.renderDisplayString(bug_level.bug_type, element.description, element.fix_suggestion, element.test_input, self.workspace)));
                        // }
                        // console.log(`inner decorationList is ${decorationList}`);
                    });
                    // console.log(`decorationList is ${decorationList}`);
                    if (bug_level.bug_type === "Crash") {
                        console.log("Setting crash underlines");
                        editor.setDecorations(crashHighlight, decorationList);
                    }
                    if (bug_level.bug_type === "Accuracy") {
                        console.log("Setting accuracy underlines");
                        editor.setDecorations(accuracyHighlight, decorationList);
                    }
                    if (bug_level.bug_type === "Dead Code") {
                        console.log("Setting dead code underlines");
                        editor.setDecorations(deadcodeHighlight, decorationList);
                    }
                    ;
                });
            });
        });
        // Register this on ChangeActiveTextEditor event so that if we open another text editor,
        // it automatically updates the new editor as well
        // Only register if changeHandle is NULL
        if (!changeHandle) {
            changeHandle = vscode_1.window.onDidChangeActiveTextEditor(() => {
                this.updateJsonDecorations();
            });
        }
    }
    ;
    unhighlightAll() {
        vscode_1.window.visibleTextEditors.forEach((editor) => {
            let decorationList = [];
            console.log("Removing dead code underlines");
            //this.logging.appendLIne("Removing dead code underlines");
            editor.setDecorations(deadcodeHighlight, decorationList);
            console.log("Removing crash underlines");
            //this.logging.appendLIne("Removing crash underlines");
            editor.setDecorations(crashHighlight, decorationList);
            console.log("Removing accuracy underlines");
            //this.logging.appendLIne("Removing accuracy underlines");
            editor.setDecorations(accuracyHighlight, decorationList);
        });
        // If a changeHandle exists, dispose it, then set it to NULL
        // so future calls to highlight will register another handle
        changeHandle === null || changeHandle === void 0 ? void 0 : changeHandle.dispose();
        changeHandle = null;
    }
    // Currently not used.
    // There are two ways to provide Hover functionality
    // 1. implement this provide Hover function
    // 2. pass in a HoverMessage in the highlighting part
    provideHover(document, position, token) {
        // console.log("Calling provideHover");
        var res = this.retrieveInJson(position, document.fileName);
        return new vscode_1.Hover(res);
    }
}
exports.OutputHighlight = OutputHighlight;
//# sourceMappingURL=highlight.js.map