import {TreeDataProvider, TreeItem, Event, ProviderResult, TreeItemCollapsibleState, TextDocumentShowOptions, Uri, Command, Range, workspace, TextDocument} from 'vscode';
import * as path from 'path';
import * as vscode from 'vscode';
import {lineCount, linesCountMultiple} from './utils';

export class BugsProvider implements TreeDataProvider<TreeItem> {
	jsonFile: string;
	mainJson: any;
	private _onDidChangeTreeData: vscode.EventEmitter<FunctionsTreeItem | undefined | null | void> = new vscode.EventEmitter<FunctionsTreeItem | undefined | null | void>();
	readonly onDidChangeTreeData: vscode.Event<FunctionsTreeItem | undefined | null | void> = this._onDidChangeTreeData.event;

	data: FunctionsTreeItem[];
  
	constructor(jsonFile: string) {
		this.jsonFile = jsonFile;
		this.mainJson = require(`${jsonFile}`);
		this.data = this.mainJson.map(toTreeItemFunc);
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

  
	refresh(): void {
		console.log(`refresh for treeViewError activated, JSON file set to ${this.jsonFile}`);
		delete require.cache[require.resolve(`${this.jsonFile}`)];
		this.mainJson = require(`${this.jsonFile}`);
		this.data = this.mainJson.map(toTreeItemFunc);
		this._onDidChangeTreeData.fire();
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
function toTreeItemFunc(element: any): FunctionsTreeItem {
	// Corresponds to the bug type node
	if (element.bug_type !== undefined) {
		return new FunctionsTreeItem(element.bug_type.concat(" Failures"), "bug_type", element.code_file, element.bugs?.map(toTreeItemFunc), element.lines_of_code);
	}
	// Corresponds to the error node
	if (element.description !== undefined) {
		return new FunctionsTreeItem(element.function_name.concat(": ").concat(element.description), "error", element.code_file, concatArrays(element.bugs?.map(toTreeItemFunc), element.bugs?.map(toTreeItemFunc)), element.lines_of_code);
	}
	if (element.lines_of_code === undefined) {
		return new FunctionsTreeItem(element.function_name.concat(": ").concat(element.description), "error", element.code_file, concatArrays(element.bugs?.map(toTreeItemFunc), element.bugs?.map(toTreeItemFunc)), [1]);
	}
	throw 'toTreeItemFunc: encountered unexpected cases';
}

class FunctionsTreeItem extends TreeItem {
	children: FunctionsTreeItem[]|undefined;
	
	constructor(label: string, nature: string, filePath: string, children?: FunctionsTreeItem[], linesOfCode?: number[]) {
		super(
			label,
			children === undefined ? TreeItemCollapsibleState.None :
									TreeItemCollapsibleState.Expanded);
		this.children = children;
		this.iconPath = determineIcon(nature);
		this.contextValue = nature;
		
		console.log(`constructor: ${filePath}`);

		// If not a folder, then display the relevant editor when clicked
		if (nature !== "bug_type") {
			if (linesOfCode !== undefined) {
				this.command = <Command>{
					title: "",
					command: "vscode.open",
					arguments: [
						Uri.file(filePath),
						determineRange(filePath, linesOfCode)]
				};
			}
		}
	}
}

// Highlights the start of first line and end of last line
function determineRange(filePath: string, linesOfCode?: number[]): TextDocumentShowOptions|undefined {
	// Call lineCount (which in turn calls file system) to get the number of characters on a line
	// Needed for highlight information for vscode.open
	console.log(`linesOfCode is ${linesOfCode}`);
	if (linesOfCode === undefined) {
		return <TextDocumentShowOptions>{
			selection: new Range(0,0,0,0)
		};
	}
	if (linesOfCode.length === undefined) {
		return <TextDocumentShowOptions>{
			selection: new Range(0,0,0,0)
		};
	}
	return <TextDocumentShowOptions>{
		selection: new Range(linesOfCode[0] - 1, 0, linesOfCode[linesOfCode.length - 1] - 1,lineCount(filePath, linesOfCode[linesOfCode.length - 1] - 1))
	};
}	

function determineIcon(nature: string) {
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