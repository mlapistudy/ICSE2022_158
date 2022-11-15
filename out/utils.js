"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.executeSync = exports.execute = exports.linesCountMultiple = exports.lineCount = void 0;
const fs_1 = __importDefault(require("fs"));
const { execSync, spawn } = require("child_process");
// Returns the number of characters on Line line_nb in file filePath
function lineCount(filePath, line_nb) {
    let text = fs_1.default.readFileSync(filePath).toString('utf-8').split("\n");
    return text[line_nb].length;
}
exports.lineCount = lineCount;
function linesCountMultiple(filePath, lines_of_code) {
    let text = fs_1.default.readFileSync(filePath).toString('utf-8').split("\n");
    let sum = 0;
    if (lines_of_code === undefined) {
        return 0;
    }
    for (let i = lines_of_code[0] - 1; i < lines_of_code[1]; i++) {
        sum = sum + text[i].length;
    }
    return sum;
}
exports.linesCountMultiple = linesCountMultiple;
// This is a wrapper for the spawn method
// callback is a function to be executed after the invoked child process finishes
function execute(cmd, callback, logging) {
    const spwanedProcess = spawn(cmd, [], { shell: true, detached: true });
    console.log(`spawned pid ${spwanedProcess.pid} with command ${cmd}`);
    spwanedProcess.stdout.on('data', (data) => {
        // This removes line breaks at start/end of string
        // needed because print statements in python generates such newline characters
        logging === null || logging === void 0 ? void 0 : logging.appendLine(data.toString().replace(/^\n|\n$/g, ''));
    });
    spwanedProcess.stderr.on('data', (data) => {
        console.error(`spawned pid ${spwanedProcess.pid} pushed something to stderr`);
        logging === null || logging === void 0 ? void 0 : logging.appendLine(data.toString().replace(/^\n|\n$/g, ''));
    });
    // when the spawn child process exits, check if there were any errors and issue the callback function
    spwanedProcess.on('exit', function (code) {
        if (code !== 0) {
            console.log('Failed: ' + code);
        }
        else {
            console.log(`pid ${spwanedProcess.pid} finished`);
        }
        callback(code);
    });
}
exports.execute = execute;
// This is the original function that uses execSync, however taking into account of
// the issue mentioned here: https://stackoverflow.com/questions/63796633/spawnsync-bin-sh-enobufs
// it does not output anything
function executeSync(cmd, logging) {
    execSync(cmd, { stdio: 'ignore' });
}
exports.executeSync = executeSync;
//# sourceMappingURL=utils.js.map