import { QuickPickItem, window, Disposable, CancellationToken, QuickInputButton, QuickInput, ExtensionContext, QuickInputButtons, Uri } from 'vscode';
import * as path from 'path';
import * as vscode from 'vscode';
import { execute, executeSync } from './utils';

const mainToolPath: string = path.join(path.dirname(path.dirname(__dirname)), "testing_tool", "my_tool");

export async function multiStepInput(func: string, codeFile: string, linenb: number, inputslst: string[], root:string, workspace:string, userInput: string, logging: vscode.OutputChannel): Promise<any>{

	// Selection of input types
	const inputtypes: QuickPickItem[] = ['string', 'integer', 'float', 'boolean', 'other']
		.map(label => ({ label }));
	
	const yesno: QuickPickItem[] = ['yes', 'no'].map(label => ({ label }));

	// Needed to record user inputs
	interface State {
		types: string;
		params: string;
	}
	
	// Launch the multi step input by running this function
	async function collectInputs() {
		const state = {types: '', params: ''} as Partial<State>;
		await MultiStepInput.run(input => pickType(input, state, 1));
		return state;
	}
	
	// Function creates a QuickPick, where user chooses type of parameter.
	async function pickType(input: MultiStepInput, state: Partial<State>, index: number) : Promise<any> {
		const pick = await input.showQuickPick({
			title: 'function:  '+func+', parameter: '+ inputslst[index-1],
			placeholder: 'Pick a type for input '+ index +': '+  inputslst[index-1],
			items: inputtypes,
			shouldResume: shouldResume
		});
		// This will launch an Input Box where the user can input their own type.
		if (pick.label === 'other') {
			return (input: MultiStepInput) => inputOtherType(input, state, index, '');
		}
		// This will prompt the multi step input to go onto the next parameter.
		else {
			state.types += ', ' + pick.label;
			if (inputslst.length > 1) {
				return (input: MultiStepInput) => inputAPIParam(input, state, index);
			}
			else {
				state.params += ', ' + inputslst[index-1];
			}
		}
	}

	// Function creates a InputBox, where user inputs their own type.
	async function inputOtherType(input: MultiStepInput, state: Partial<State>, index: number, placeholder: string) {
		placeholder = await input.showInputBox({
			title: func+' inputs',
			value: typeof placeholder === 'string' ? placeholder : '',
			prompt: 'Choose a type for input ' + index,
			validate: validateNameIsUnique,
			shouldResume: shouldResume
		});
		state.types += ', ' + placeholder;
		if (inputslst.length > 1) {
			return (input: MultiStepInput) => inputAPIParam(input, state, index);
		}
		else {
			state.params += ', ' + inputslst[index-1];
		}
	}

	async function inputAPIParam(input: MultiStepInput, state: Partial<State>, index: number) {
		const pick = await input.showQuickPick({
			title: 'In the function '+func+' is '+inputslst[index-1]+' used in the ML API?',
			placeholder: 'Is ' + inputslst[index-1] + ' used in the ML API',
			items: yesno,
			shouldResume: shouldResume
		});
		if (pick.label === 'yes') {
			state.params += ', ' + inputslst[index-1];
		}
		if (index < inputslst.length) {
			return (input: MultiStepInput) => pickType(input, state, index+1);
		}
	}

	function shouldResume() {
		// Could show a notification with the option to resume.
		return new Promise<boolean>((resolve, reject) => {
			// noop
		});
	}

	async function validateNameIsUnique(name: string) {
		// ...validate...
		await new Promise(resolve => setTimeout(resolve, 1000));
		return name === 'vscode' ? 'Name not unique' : undefined;
	}

	let typesinput = " ";
	let params = " ";
	// launch multi step input
	if (inputslst.length > 0) {
		const t = await collectInputs();
		if (t.types !== undefined && t.params !== undefined) {
			typesinput = typesinput.substring(1).concat(t.types);
			params = params.substring(1).concat(t.params);
		}
	}
	
	// create json file with input type information
	// NOTE: user input is not needed because this python file can be easily executed in any env
	let cmd = `cd ${root}; python type_output.py -f '${func}' -t '${typesinput.substring(1)}' -d '${workspace}' -n '${linenb}' -cf '${codeFile}' -p '${params.substring(1)}'`;

	executeSync(cmd); 
	window.showInformationMessage(`Your input has been collected! Now running our testing tool. You can click the button below to view progress in logging`, 'Log Messages').then(selection => {
		if (selection === 'Log Messages') {
			logging.show();
		}
	});

	const mainToolPath: string = path.join(path.dirname(path.dirname(__dirname)), "testing_tool", "my_tool");
	const exportPaths: string = "";
	const inputJson: string = path.join(workspace, '/.vscode/tool_json_files/user_input.json');
	const outputJson: string = path.join(workspace, '/.vscode/tool_json_files/bugs.json');
	const logsJson: string = path.join(workspace, '/.vscode/tool_json_files/logs.txt');
	cmd = `cd ${mainToolPath}; ${userInput} ${exportPaths} python3.8 -u all_wrap_up.py --input_json ${inputJson} --output_json ${outputJson} --log_file ${logsJson}`;
		
	execute(cmd, ((value: any) => {
		if (value !== 0) {
			window.showErrorMessage(`There was an error in finding failures, please check that you submitted the correct inputs and that you don't have simple syntax errors in your code. Click the button below to be redirected to the input file we use to find failures. Make sure all the information in this file is correct. You can also inspect our tool output here`, 'Input file', 'Log Messages')
			.then(selection => {
				if (selection === 'Input file') {
					vscode.workspace.openTextDocument(inputJson).then(iDoc => {
						vscode.window.showTextDocument(iDoc).then(editor => {});
					});
				}
				else if (selection === 'Log Messages') {
					logging.show();
				}
			});
		}
	}), logging);
}

// MultiStepInput
class InputFlowAction {
	static back = new InputFlowAction();
	static cancel = new InputFlowAction();
	static resume = new InputFlowAction();
}

type InputStep = (input: MultiStepInput) => Thenable<InputStep | void>;

interface QuickPickParameters<T extends QuickPickItem> {
	title: string;
	items: T[];
	activeItem?: T;
	placeholder: string;
	buttons?: QuickInputButton[];
	shouldResume: () => Thenable<boolean>;
}

interface InputBoxParameters {
	title: string;
	value: string;
	prompt: string;
	validate: (value: string) => Promise<string | undefined>;
	buttons?: QuickInputButton[];
	shouldResume: () => Thenable<boolean>;
}

class MultiStepInput {

	static async run<T>(start: InputStep) {
		const input = new MultiStepInput();
		return input.stepThrough(start);
	}

	private current?: QuickInput;
	private steps: InputStep[] = [];

	private async stepThrough<T>(start: InputStep) {
		let step: InputStep | void = start;
		while (step) {
			this.steps.push(step);
			if (this.current) {
				this.current.enabled = false;
				this.current.busy = true;
			}
			try {
				step = await step(this);
			} catch (err) {
				if (err === InputFlowAction.back) {
					this.steps.pop();
					step = this.steps.pop();
				} else if (err === InputFlowAction.resume) {
					step = this.steps.pop();
				} else if (err === InputFlowAction.cancel) {
					step = undefined;
				} else {
					throw err;
				}
			}
		}
		if (this.current) {
			this.current.dispose();
		}
	}

	async showQuickPick<T extends QuickPickItem, P extends QuickPickParameters<T>>({ title, items, activeItem, placeholder, buttons, shouldResume }: P) {
		const disposables: Disposable[] = [];
		try {
			return await new Promise<T | (P extends { buttons: (infer I)[] } ? I : never)>((resolve, reject) => {
				const input = window.createQuickPick<T>();
				input.title = title;
				input.placeholder = placeholder;
				input.items = items;
				if (activeItem) {
					input.activeItems = [activeItem];
				}
				input.buttons = [
					...(this.steps.length > 1 ? [QuickInputButtons.Back] : []),
					...(buttons || [])
				];
				disposables.push(
					input.onDidTriggerButton(item => {
						if (item === QuickInputButtons.Back) {
							reject(InputFlowAction.back);
						} else {
							resolve(<any>item);
						}
					}),
					input.onDidChangeSelection(items => resolve(items[0])),
					input.onDidHide(() => {
						(async () => {
							reject(shouldResume && await shouldResume() ? InputFlowAction.resume : InputFlowAction.cancel);
						})()
							.catch(reject);
					})
				);
				if (this.current) {
					this.current.dispose();
				}
				this.current = input;
				this.current.show();
			});
		} finally {
			disposables.forEach(d => d.dispose());
		}
	}

	async showInputBox<P extends InputBoxParameters>({ title, value, prompt, validate, buttons, shouldResume }: P) {
		const disposables: Disposable[] = [];
		try {
			return await new Promise<string | (P extends { buttons: (infer I)[] } ? I : never)>((resolve, reject) => {
				const input = window.createInputBox();
				input.title = title;
				input.value = value || '';
				input.prompt = prompt;
				input.buttons = [
					...(this.steps.length > 1 ? [QuickInputButtons.Back] : []),
					...(buttons || [])
				];
				let validating = validate('');
				disposables.push(
					input.onDidTriggerButton(item => {
						if (item === QuickInputButtons.Back) {
							reject(InputFlowAction.back);
						} else {
							resolve(<any>item);
						}
					}),
					input.onDidAccept(async () => {
						const value = input.value;
						input.enabled = false;
						input.busy = true;
						if (!(await validate(value))) {
							resolve(value);
						}
						input.enabled = true;
						input.busy = false;
					}),
					input.onDidChangeValue(async text => {
						const current = validate(text);
						validating = current;
						const validationMessage = await current;
						if (current === validating) {
							input.validationMessage = validationMessage;
						}
					}),
					input.onDidHide(() => {
						(async () => {
							reject(shouldResume && await shouldResume() ? InputFlowAction.resume : InputFlowAction.cancel);
						})()
							.catch(reject);
					})
				);
				if (this.current) {
					this.current.dispose();
				}
				this.current = input;
				this.current.show();
			});
		} finally {
			disposables.forEach(d => d.dispose());
		}
	}
}