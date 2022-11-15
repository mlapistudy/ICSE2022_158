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
exports.BugsProvider = void 0;
const vscode_1 = require("vscode");
const path = __importStar(require("path"));
const vscode = __importStar(require("vscode"));
const utils_1 = require("./utils");
class BugsProvider {
    constructor(jsonFile) {
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
        this.jsonFile = jsonFile;
        this.mainJson = require(`${jsonFile}`);
        this.data = this.mainJson.map(toTreeItemFunc);
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
    refresh() {
        console.log(`refresh for treeViewError activated, JSON file set to ${this.jsonFile}`);
        delete require.cache[require.resolve(`${this.jsonFile}`)];
        this.mainJson = require(`${this.jsonFile}`);
        this.data = this.mainJson.map(toTreeItemFunc);
        this._onDidChangeTreeData.fire();
    }
}
exports.BugsProvider = BugsProvider;
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
function toTreeItemFunc(element) {
    var _a, _b, _c, _d, _e;
    // Corresponds to the bug type node
    if (element.bug_type !== undefined) {
        return new FunctionsTreeItem(element.bug_type.concat(" Failures"), "bug_type", element.code_file, (_a = element.bugs) === null || _a === void 0 ? void 0 : _a.map(toTreeItemFunc), element.lines_of_code);
    }
    // Corresponds to the error node
    if (element.description !== undefined) {
        return new FunctionsTreeItem(element.function_name.concat(": ").concat(element.description), "error", element.code_file, concatArrays((_b = element.bugs) === null || _b === void 0 ? void 0 : _b.map(toTreeItemFunc), (_c = element.bugs) === null || _c === void 0 ? void 0 : _c.map(toTreeItemFunc)), element.lines_of_code);
    }
    if (element.lines_of_code === undefined) {
        return new FunctionsTreeItem(element.function_name.concat(": ").concat(element.description), "error", element.code_file, concatArrays((_d = element.bugs) === null || _d === void 0 ? void 0 : _d.map(toTreeItemFunc), (_e = element.bugs) === null || _e === void 0 ? void 0 : _e.map(toTreeItemFunc)), [1]);
    }
    throw 'toTreeItemFunc: encountered unexpected cases';
}
class FunctionsTreeItem extends vscode_1.TreeItem {
    constructor(label, nature, filePath, children, linesOfCode) {
        super(label, children === undefined ? vscode_1.TreeItemCollapsibleState.None :
            vscode_1.TreeItemCollapsibleState.Expanded);
        this.children = children;
        this.iconPath = determineIcon(nature);
        this.contextValue = nature;
        console.log(`constructor: ${filePath}`);
        // If not a folder, then display the relevant editor when clicked
        if (nature !== "bug_type") {
            if (linesOfCode !== undefined) {
                this.command = {
                    title: "",
                    command: "vscode.open",
                    arguments: [
                        vscode_1.Uri.file(filePath),
                        determineRange(filePath, linesOfCode)
                    ]
                };
            }
        }
    }
}
// Highlights the start of first line and end of last line
function determineRange(filePath, linesOfCode) {
    // Call lineCount (which in turn calls file system) to get the number of characters on a line
    // Needed for highlight information for vscode.open
    console.log(`linesOfCode is ${linesOfCode}`);
    if (linesOfCode === undefined) {
        return {
            selection: new vscode_1.Range(0, 0, 0, 0)
        };
    }
    if (linesOfCode.length === undefined) {
        return {
            selection: new vscode_1.Range(0, 0, 0, 0)
        };
    }
    return {
        selection: new vscode_1.Range(linesOfCode[0] - 1, 0, linesOfCode[linesOfCode.length - 1] - 1, utils_1.lineCount(filePath, linesOfCode[linesOfCode.length - 1] - 1))
    };
}
function determineIcon(nature) {
    if (nature === "bug_type") {
        console.log("determineIcon: bug_type");
        return {
            light: path.join(__filename, '..', '..', 'resources', 'bug.svg'),
            dark: path.join(__filename, '..', '..', 'resources', 'bug.svg')
        };
    }
    if (nature === "error") {
        return {
            light: path.join(__filename, '..', '..', 'resources', 'function-svgrepo-com.svg'),
            dark: path.join(__filename, '..', '..', 'resources', 'function-svgrepo-com.svg')
        };
    }
}
//# sourceMappingURL=treeViewError.js.map