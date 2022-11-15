'use strict'
import { execSync } from 'child_process';
import * as vscode from 'vscode';
import * as path from 'path';
const fs = require('fs')
import { HoverProvider, Hover, MarkdownString, window, Range, Position, TextEditorDecorationType, CancellationToken, TextDocument, ProviderResult, DecorationOptions, TextEditorCursorStyle, TextEditor, Disposable} from 'vscode';

// Stores the handle (actually type Disposable but has to set to any for NULL compatibility)
// returned by registerring to an event
let changeHandle: any = null;

// TODO: Figure out better decoration types with support for different themes
const accuracyHighlight = window.createTextEditorDecorationType({
    // isWholeLine: false,
    // backgroundColor: new ThemeColor('red'),
    borderWidth: `0 0 3px 0`,
    borderStyle: `dotted`,
    borderColor: `red`
    // color: new ThemeColor("#fc8403")
});

const deadcodeHighlight= window.createTextEditorDecorationType({
    borderWidth: `0 0 3px 0`,
    borderStyle: `dotted`,
    borderColor: `blue`
});

const crashHighlight = window.createTextEditorDecorationType({
    borderWidth: `0 0 3px 0`,
    borderStyle: `dotted`,
    borderColor: `yellow`
});


// Hover implementation
export class OutputHighlight {
    mainJson: any;
    jsonFile: string;
    workspace: string;
    logging: vscode.OutputChannel;
    currentTextIndex: number;

    constructor(jsonFile: string, workspace: string, logging: vscode.OutputChannel) {
        this.jsonFile = jsonFile;
        this.mainJson = require(`${jsonFile}`);
        this.workspace = workspace;
        this.logging = logging;
        this.currentTextIndex = 0;
        console.log(`Executed MLAPIHoverProvider constructor, JSON file set to ${jsonFile}`);
    }

    refresh(): void {
		console.log(`refresh for Output Highlight activated, JSON file set to ${this.jsonFile}`);
		delete require.cache[require.resolve(`${this.jsonFile}`)];
		this.mainJson = require(`${this.jsonFile}`);
	}

    positionWithinLine(position: Position, line: number[]): boolean {
        return line.includes(position.line);
    };

    // Renders the string to be displayed on hover
    renderDisplayString(bug_type: string, description: string, fix_suggestion: string, test_input: any[], workspace: string): MarkdownString {
        let res: MarkdownString = new MarkdownString();
        res.appendMarkdown(`**Failure Type**: ${bug_type} Failure\n\n***\n\n`);
        res.appendMarkdown(`**Description**: ${description}\n\n***\n\n`);
        if (fix_suggestion !== undefined) {
            res.appendMarkdown(`**Fix Suggestion**:\n\n${fix_suggestion}\n\n***\n\n`);
        }
        if (test_input !== undefined) {
            res.appendMarkdown("**Failure Triggering Input**:\n\n");
            // each test_input is a key-value pair
            test_input.forEach((element: any[], index: number) => {
                this.currentTextIndex ++;
                Object.entries(element).forEach(([key, value]: [string, string]) => {
                    // console.log(`Number ${this.currentTextIndex} is key, value pair is ${key}, ${value}`);
                    // Matching value with filepath in RegEx
                    if (fs.existsSync(value)) {
                        console.log(`string ${value} as a file exists`);
                        res.appendMarkdown(`[Click here to see image input ${this.currentTextIndex}](${value})  \n`);
                    }
                    else {
                        const textInput: string = path.join(workspace, `/.vscode/tool_json_files/textinput_${this.currentTextIndex}.txt`);
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
                        execSync(`echo ${value} > ${textInput}`);
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
    updateDecorations(fileToUpdate: string, updateLines: number[], editor: TextEditor, hoverMessage: MarkdownString): DecorationOptions[] {
        let decorationList: DecorationOptions[] = [];

        // console.log(`editor pointing to ${editor.document.fileName}`);
        // console.log(`fileToUpdate from JSON pointing to ${fileToUpdate}`);

        // Check if the editor's filename corresponds to the desired file to be updated
        if (editor.document.fileName === fileToUpdate) {
            updateLines.forEach((updateLine: number) => {
                updateLine -= 1;
                let endLineText = editor.document.lineAt(updateLine);

                // Because the Range operator expects character information, 0 and the Math.max are character information
                decorationList.push({range: new Range(updateLine, 0, updateLine, Math.max(endLineText.text.length, 0)), hoverMessage: hoverMessage});
                console.log(`underlining line ${updateLine} upto ${Math.max(endLineText.text.length, 0)}`);
                //this.logging.appendLIne(`underlining line ${updateLine} upto ${Math.max(endLineText.text.length, 0)}`);
            });
        }
        return decorationList;
    }

    // Currently unused
    retrieveInJson(position: Position, codeFile: string): MarkdownString[] {
        var res: MarkdownString[] = [];
        this.mainJson.forEach((element: { lines_of_code: number[]; bug_type: string; description: string; fix_suggestion: string; code_file: string; test_input: any[]}) => {
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
    public updateJsonDecorations() {
        // Iterate through all bug types first
        ["Crash", "Accuracy", "Dead Code"].forEach((bug_type) => {
            // Iterate through all text editors
            // Assemble a decoration list for each text editor + each bug type
            // Each bug type corresponds to the `bug_level` iteration, i.e., the top level of json file
            // The reason for this is we can only call editor.setDecorations with one style once
            // If we call it with the same style twice, then the second one replaces the effect of the first one
            window.visibleTextEditors.forEach((editor) => {
                this.currentTextIndex = 0;
                var self = this;
                this.mainJson.forEach(function(bug_level: {bug_type: string; bugs: any[]}) {
                    let decorationList: DecorationOptions[] = [];
                    bug_level.bugs.forEach(function(element: { lines_of_code: number[]; bug_type: string; code_file: string; description: string; fix_suggestion: string; test_input: any[]}) {
                        // if (bug_level.bug_type === element.bug_type) {
                        decorationList = decorationList.concat(self.updateDecorations(element.code_file, element.lines_of_code, editor, self.renderDisplayString(bug_level.bug_type, element.description, element.fix_suggestion, element.test_input, self.workspace)));
                        // }
                        // console.log(`inner decorationList is ${decorationList}`);
                    });
                    // console.log(`decorationList is ${decorationList}`);
                    if (bug_level.bug_type === "Crash") {console.log("Setting crash underlines"); editor.setDecorations(crashHighlight, decorationList);}
                    if (bug_level.bug_type === "Accuracy") {console.log("Setting accuracy underlines"); editor.setDecorations(accuracyHighlight, decorationList);}
                    if (bug_level.bug_type === "Dead Code") {console.log("Setting dead code underlines"); editor.setDecorations(deadcodeHighlight, decorationList);};
                });
            });
        });

        // Register this on ChangeActiveTextEditor event so that if we open another text editor,
        // it automatically updates the new editor as well
        // Only register if changeHandle is NULL
        if (!changeHandle) {
            changeHandle = window.onDidChangeActiveTextEditor(() => {
                this.updateJsonDecorations();
            });
        }
    };

    public unhighlightAll() {
        window.visibleTextEditors.forEach((editor) => {
            let decorationList: DecorationOptions[] = [];
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
        changeHandle?.dispose();
        changeHandle = null;
    }

    // Currently not used.
    // There are two ways to provide Hover functionality
    // 1. implement this provide Hover function
    // 2. pass in a HoverMessage in the highlighting part
    public provideHover(
        document: TextDocument, position: Position, token: CancellationToken):
        ProviderResult<Hover> {
            // console.log("Calling provideHover");
            var res: MarkdownString[] = this.retrieveInJson(position, document.fileName);
            return new Hover(res);
    }
}

// function getDecorationTypeFromConfig() {
//     const config = workspace.getConfiguration("highlightLine")
//     const borderColor = config.get("borderColor");
//     const borderWidth = config.get("borderWidth");
//     const borderStyle = config.get("borderStyle");
//     const decorationType = window.createTextEditorDecorationType({
//         isWholeLine: true,
//         borderWidth: `0 0 ${borderWidth} 0`,
//         borderStyle: `${borderStyle}`, //TODO: file bug, this shouldn't throw a lint error.
//         borderColor: `${borderColor}`
//     })
//     return decorationType;
// }
