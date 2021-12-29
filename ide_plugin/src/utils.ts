import fs from 'fs';
import * as vscode from 'vscode';
const { execSync, spawn } = require("child_process");

// Returns the number of characters on Line line_nb in file filePath
export function lineCount(filePath: string, line_nb: number ) {
    let text: string[] = fs.readFileSync(filePath).toString('utf-8').split("\n");
    return text[line_nb].length;
}

export function linesCountMultiple(filePath: string, lines_of_code?: number[] ) {
    let text: string[] = fs.readFileSync(filePath).toString('utf-8').split("\n");
    let sum: number = 0;
    if (lines_of_code === undefined) {
		return 0;
	}
    for (let i = lines_of_code[0]-1; i < lines_of_code[1]; i++) {
        sum = sum+text[i].length;
      }
    return sum;
}


// This is a wrapper for the spawn method
// callback is a function to be executed after the invoked child process finishes
export function execute(cmd: string, callback: any, logging?: vscode.OutputChannel) {
    const spwanedProcess = spawn(cmd, [], {shell: true, detached: true});
    console.log(`spawned pid ${spwanedProcess.pid} with command ${cmd}`);
    spwanedProcess.stdout.on('data', (data: any) => {
        // This removes line breaks at start/end of string
        // needed because print statements in python generates such newline characters
        logging?.appendLine(data.toString().replace(/^\n|\n$/g, ''));
    });
    spwanedProcess.stderr.on('data', (data: any) => {
        console.error(`spawned pid ${spwanedProcess.pid} pushed something to stderr`);
        logging?.appendLine(data.toString().replace(/^\n|\n$/g, ''));
    });
    // when the spawn child process exits, check if there were any errors and issue the callback function
    spwanedProcess.on('exit', function(code: any) {
        if (code !== 0) {
            console.log('Failed: ' + code);
        }
        else {
            console.log(`pid ${spwanedProcess.pid} finished`);
        }
        callback(code);
    });
}

// This is the original function that uses execSync, however taking into account of
// the issue mentioned here: https://stackoverflow.com/questions/63796633/spawnsync-bin-sh-enobufs
// it does not output anything
export function executeSync(cmd: string, logging?: vscode.OutputChannel) {
	execSync(cmd, { stdio: 'ignore' });
}