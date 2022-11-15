import {TreeDataProvider, TreeItem, Event, ProviderResult, TreeItemCollapsibleState, TextDocumentShowOptions, Uri, Command, Range, workspace, TextDocument} from 'vscode';
import * as path from 'path';
import * as vscode from 'vscode';
import {lineCount} from './utils';

export class TestableFunctionsProvider implements TreeDataProvider<TreeItem> {
	mainJson: any;
	jsonFile: string;
	// onDidChangeTreeData?: Event<FunctionsTreeItem|null|undefined>|undefined;
	private _onDidChangeTreeData: vscode.EventEmitter<FunctionsTreeItem | undefined | null | void> = new vscode.EventEmitter<FunctionsTreeItem | undefined | null | void>();
	readonly onDidChangeTreeData: vscode.Event<FunctionsTreeItem | undefined | null | void> = this._onDidChangeTreeData.event;

	data: FunctionsTreeItem[];
  
	constructor(jsonFile: string) {
		this.jsonFile = jsonFile;
		this.mainJson = require(`${jsonFile}`);
		// The top layer is empty. All information is contained in the children field
		// of the top layer
		this.data = this.mainJson.children.map(toTreeItem);
		console.log(`treeView (testable function) registered with JSON file set to ${this.jsonFile}`);
	}

	refresh(): void {
		console.log(`refresh for treeView (testable function) activated, JSON file set to ${this.jsonFile}`);
		delete require.cache[require.resolve(`${this.jsonFile}`)];
		this.mainJson = require(`${this.jsonFile}`);
		console.log(`treeView (testable function) finished reading JSON file, mapping infomation...`);
		this.data = this.mainJson.children.map(toTreeItem);
		this._onDidChangeTreeData.fire();
	}
  
	getTreeItem(element: FunctionsTreeItem): FunctionsTreeItem|Thenable<FunctionsTreeItem> {
	  return element;
	}
  
	getChildren(element?: FunctionsTreeItem|undefined): ProviderResult<FunctionsTreeItem[]> {
		if (element === undefined) {
			// The data has already been fully constructed at this point
			return this.data;
	  }
	  return element.children;
	}
}

function concatArrays(arr1: any[], arr2: any[]): any {
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
function toTreeItem(element: any): FunctionsTreeItem {
	// Corresponds to the directory node
	if (element.directory !== undefined) {
		return new FunctionsTreeItem(element.directory, "directory", element.code_file, element.children?.map(toTreeItem), element.line_nb);
	}
	// Corresponds to the file node
	if (element.nature === "MODULE") {
		return new FunctionsTreeItem(element.name, "file", element.code_file, element.children?.map(toTreeItem));
	}
	// Corresponds to the class node
	if (element.nature === "CLASS") {
		return new FunctionsTreeItem(element.name, "class", element.code_file, element.children?.map(toTreeItem), element.line_nb);
	}
	// Corresponds to the function node
	if (element.nature === "FUNCTION") {
		return new FunctionsTreeItem(element.name, "function", element.code_file, element.children?.map(toTreeItem), element.line_nb, element.args);
	}
	throw 'toTreeItem: encountered unexpected cases';
}

class FunctionsTreeItem extends TreeItem {
	children: FunctionsTreeItem[]|undefined;
	lineNb?: number;
	filePath: string;
	args?: string[];         // Only applies to function nodes

	constructor(label: string, nature: string, filePath: string, children?: FunctionsTreeItem[], lineNb?: number, args?: string[]) {
		super(
			label,
			children === undefined ? TreeItemCollapsibleState.None :
									TreeItemCollapsibleState.Expanded);
		this.children = children;
		this.iconPath = determineIcon(nature);
		this.contextValue = nature;
		this.lineNb = lineNb;
		this.filePath = filePath;
		this.args = args;
		
		// console.log(`constructor: ${filePath}`);
		// If not a folder, then display the relevant editor when clicked
		if (nature !== "directory") {
			this.command = <Command>{
				title: "",
				command: "vscode.open",
				arguments: [
					Uri.file(filePath),
					determineRange(filePath, lineNb)]
			};
		}
	}
}

function determineRange(filePath: string, lineNb?: number): TextDocumentShowOptions|undefined {
	// If lineNb is undefined, then this is a file, so just return start of the file
	if (lineNb === undefined) {
		return <TextDocumentShowOptions>{
			selection: new Range(0,0,0,0)
		};
	}

	// Call lineCount (which in turn calls file system) to get the number of characters on a line
	// Needed for highlight information for vscode.open
	return <TextDocumentShowOptions>{
		selection: new Range(lineNb - 1, 0, lineNb - 1,lineCount(filePath, lineNb - 1))
	};
}

function determineIcon(nature: string) {
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