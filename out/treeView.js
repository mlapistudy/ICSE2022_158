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
exports.TestableFunctionsProvider = void 0;
const vscode_1 = require("vscode");
const path = __importStar(require("path"));
const vscode = __importStar(require("vscode"));
const utils_1 = require("./utils");
class TestableFunctionsProvider {
    constructor(jsonFile) {
        // onDidChangeTreeData?: Event<FunctionsTreeItem|null|undefined>|undefined;
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
        this.jsonFile = jsonFile;
        this.mainJson = require(`${jsonFile}`);
        // The top layer is empty. All information is contained in the children field
        // of the top layer
        this.data = this.mainJson.children.map(toTreeItem);
        console.log(`treeView (testable function) registered with JSON file set to ${this.jsonFile}`);
    }
    refresh() {
        console.log(`refresh for treeView (testable function) activated, JSON file set to ${this.jsonFile}`);
        delete require.cache[require.resolve(`${this.jsonFile}`)];
        this.mainJson = require(`${this.jsonFile}`);
        console.log(`treeView (testable function) finished reading JSON file, mapping infomation...`);
        this.data = this.mainJson.children.map(toTreeItem);
        this._onDidChangeTreeData.fire();
    }
    getTreeItem(element) {
        return element;
    }
    getChildren(element) {
        if (element === undefined) {
            // The data has already been fully constructed at this point
            return this.data;
        }
        return element.children;
    }
}
exports.TestableFunctionsProvider = TestableFunctionsProvider;
function concatArrays(arr1, arr2) {
    if (arr1 !== undefined && arr2 !== undefined) {
        return arr1.concat(arr2);
    }
    else if (arr1 !== undefined) {
        return arr1;
    }
    else if (arr2 !== undefined) {
        return arr2;
    }
    else {
        return undefined;
    }
}
// Function to be applied on MAP
function toTreeItem(element) {
    var _a, _b, _c, _d;
    // Corresponds to the directory node
    if (element.directory !== undefined) {
        return new FunctionsTreeItem(element.directory, "directory", element.code_file, (_a = element.children) === null || _a === void 0 ? void 0 : _a.map(toTreeItem), element.line_nb);
    }
    // Corresponds to the file node
    if (element.nature === "MODULE") {
        return new FunctionsTreeItem(element.name, "file", element.code_file, (_b = element.children) === null || _b === void 0 ? void 0 : _b.map(toTreeItem));
    }
    // Corresponds to the class node
    if (element.nature === "CLASS") {
        return new FunctionsTreeItem(element.name, "class", element.code_file, (_c = element.children) === null || _c === void 0 ? void 0 : _c.map(toTreeItem), element.line_nb);
    }
    // Corresponds to the function node
    if (element.nature === "FUNCTION") {
        return new FunctionsTreeItem(element.name, "function", element.code_file, (_d = element.children) === null || _d === void 0 ? void 0 : _d.map(toTreeItem), element.line_nb, element.args);
    }
    throw 'toTreeItem: encountered unexpected cases';
}
class FunctionsTreeItem extends vscode_1.TreeItem {
    constructor(label, nature, filePath, children, lineNb, args) {
        super(label, children === undefined ? vscode_1.TreeItemCollapsibleState.None :
            vscode_1.TreeItemCollapsibleState.Expanded);
        this.children = children;
        this.iconPath = determineIcon(nature);
        this.contextValue = nature;
        this.lineNb = lineNb;
        this.filePath = filePath;
        this.args = args;
        // console.log(`constructor: ${filePath}`);
        // If not a folder, then display the relevant editor when clicked
        if (nature !== "directory") {
            this.command = {
                title: "",
                command: "vscode.open",
                arguments: [
                    vscode_1.Uri.file(filePath),
                    determineRange(filePath, lineNb)
                ]
            };
        }
    }
}
function determineRange(filePath, lineNb) {
    // If lineNb is undefined, then this is a file, so just return start of the file
    if (lineNb === undefined) {
        return {
            selection: new vscode_1.Range(0, 0, 0, 0)
        };
    }
    // Call lineCount (which in turn calls file system) to get the number of characters on a line
    // Needed for highlight information for vscode.open
    return {
        selection: new vscode_1.Range(lineNb - 1, 0, lineNb - 1, utils_1.lineCount(filePath, lineNb - 1))
    };
}
function determineIcon(nature) {
    // console.log("determineIcon: being called, value of this.nature is" + ` ${nature}`);
    if (nature === "file") {
        // console.log("determineIcon: file");
        return {
            light: path.join(__filename, '..', '..', 'resources', 'Python-logo-notext.svg'),
            dark: path.join(__filename, '..', '..', 'resources', 'Python-logo-notext.svg')
        };
    }
    if (nature === "directory") {
        // console.log("determineIcon: directory");
        return {
            light: path.join(__filename, '..', '..', 'resources', 'folders-svgrepo-com.svg'),
            dark: path.join(__filename, '..', '..', 'resources', 'folders-svgrepo-com.svg')
        };
    }
    if (nature === "function") {
        return {
            light: path.join(__filename, '..', '..', 'resources', 'function-svgrepo-com.svg'),
            dark: path.join(__filename, '..', '..', 'resources', 'function-svgrepo-com.svg')
        };
    }
    if (nature === "class") {
        return {
            light: path.join(__filename, '..', '..', 'resources', 'cube.svg'),
            dark: path.join(__filename, '..', '..', 'resources', 'cube.svg')
        };
    }
}
//# sourceMappingURL=treeView.js.map