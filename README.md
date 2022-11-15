# Readme

This branch contains VsCode IDE plugin for our testing tool.

Our IDE plugin is also avaliable at [VS Code marketplace](https://marketplace.visualstudio.com/items?itemName=ALERTProject.mlapitesting).

## How to launch IDE plugin
Open the **`ide_plugin/` folder** in VS Code. Please make sure it is not the parent/child folder of `ide_plugin/`, otherwise VS Code would not able to parse the project.

Change following lines to correct path in `ide_plugin/src/userinputs.ts` and `ide_plugin/src/inputFunction.ts`
```ts
const exportPaths: string = "export GOOGLE_APPLICATION_CREDENTIALS='/path/to/your/google/credential.json'; export PYTHONPATH=/usr/local/share/pyshared/;"; // Google credential & CVC4, please check ../INSTALL.md for details
```

Then select `ide_plugin/src/extension.ts`. Click "run" -> "start debugging" on top menu or pressing F5. Then the plugin interface would appear in a new VS Code window. 

We provide an example input in `ide_plugin/plugin_example`. To use this example, please open this folder in the new VS Code window.


## How to use the plugin interface
1. Click on the plugin icon on the left side of your screen to reveal the plugin window. It may take several seconds.
![Install from marketplace](https://github.com/george1459/ICSE2022_158/demo/demo1.jpeg)
2. Next, click on the refresh button in the upper right hand corner of the plugin window, or the "Detect Relevant Functions" button in the bottom third of the plugin window, in order to find functions that can be tested by our plugin.
![Install from marketplace](https://github.com/george1459/ICSE2022_158/demo/demo2.jpeg)
3. Next, click on the function you want to test and click on the button "Test This Function" located to the right of the function name. You can also input information for a function not shown in the plugin window by clicking on the "Input for testable functions" button.
![Install from marketplace](https://github.com/george1459/ICSE2022_158/demo/demo3.jpeg)
4. Next, for each of the selected function's parameters, fill out what type the parameter is and whether it is used in a Machine Learning Cloud API.
![Install from marketplace](https://github.com/george1459/ICSE2022_158/demo/demo4.jpeg)
5. Once the types have been inputted you will see a pop-up window where you can click the "Log Messages" button. Clicking this button will allow you to see the progress of our tool while it runs. Depends on the network and number of test cases, it may take several minutes to execute.
![Install from marketplace](https://github.com/george1459/ICSE2022_158/demo/demo5.jpeg)
6. Congrats! Right under the view for the testable functions you will see information about any bugs or inefficiencies your selected function has. You will also see the lines of code with bugs underlined for you! If you want to remove the underlines, click the "Remove underlines" button.
![Install from marketplace](https://github.com/george1459/ICSE2022_158/demo/demo6.jpeg)

## GIF demo
![Install from marketplace](https://github.com/george1459/ICSE2022_158/demo/demo-video.gif)
