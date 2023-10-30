## Copyright 2015-2019 Ilgar Lunin, Pedro Cabrera

## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at

##     http://www.apache.org/licenses/LICENSE-2.0

## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.


from datetime import datetime
from Qt.QtWidgets import QFileDialog
from Qt.QtWidgets import QMessageBox

from PyFlow import getRawNodeInstance
from PyFlow.Core.Common import *
from PyFlow.UI.UIInterfaces import IDataExporter
from PyFlow import getRawNodeInstance
from PyFlow.Core.version import Version
from PyFlow.Core.PyCodeCompiler import Py3CodeCompiler


def nodeToScript(node, supportedDataTypes, supportedStructures):
    script = ""
    lib = None if node.lib is None else "'{0}'".format(node.lib)
    script += "{0} = getRawNodeInstance('{1}', packageName='{2}', libName={3})\n".format(
        node.name, node.__class__.__name__, node.packageName, lib
    )
    script += "ROOT_GRAPH.addNode({0})\n".format(node.name)
    script += "{0}.setPosition({1}, {2})\n".format(node.name, node.x, node.y)
    script += "{0}.setName('{0}')\n".format(node.name)

    for inPin in node.inputs.values():
        if inPin.dataType not in supportedDataTypes:
            raise Exception(
                "Data type {0} of pin {1} is not supported!".format(
                    inPin.dataType, inPin.getFullName()
                )
            )
        if inPin.structureType not in supportedStructures:
            raise Exception(
                "Structure {0} of pin {1} is not supported!".format(
                    str(inPin.structureType), inPin.getFullName()
                )
            )

        data = (
            "'{}'".format(inPin.currentData())
            if isinstance(inPin.currentData(), str)
            else inPin.currentData()
        )
        script += "{0}['{1}'].setData({2})\n".format(node.name, inPin.name, data)

    for outPin in node.outputs.values():
        if outPin.dataType not in supportedDataTypes:
            raise Exception(
                "Data type {0} of pin {1} is not supported!".format(
                    outPin.dataType, outPin.getFullName()
                )
            )
        if outPin.structureType not in supportedStructures:
            raise Exception(
                "Structure {0} of pin {1} is not supported!".format(
                    str(outPin.structureType), outPin.getFullName()
                )
            )

        data = (
            "'{}'".format(outPin.currentData())
            if isinstance(outPin.currentData(), str)
            else outPin.currentData()
        )
        script += "{0}['{1}'].setData({2})\n".format(node.name, outPin.name, data)
    return script


class PythonScriptExporter(IDataExporter):
    """docstring for PythonScriptExporter."""

    name_filter = "PyFlow program scripts (*.py)"

    def __init__(self):
        super(PythonScriptExporter, self).__init__()

    @staticmethod
    def createImporterMenu():
        return False

    @staticmethod
    def creationDateString():
        return datetime.now().strftime("%I:%M%p on %B %d, %Y")

    @staticmethod
    def version():
        return Version(1, 0, 0)

    @staticmethod
    def toolTip():
        return "Export/Import program as python script."

    @staticmethod
    def displayName():
        return "Graph script"

    @staticmethod
    def doImport(pyFlowInstance):
        name_filter = "Graph files (*.json)"
        openFilename, filterString = QFileDialog.getOpenFileName(
            filter=PythonScriptExporter.name_filter
        )
        if openFilename != "":
            with open(openFilename, "r") as f:
                script = f.read()
                mem = Py3CodeCompiler().compile(code=script, scope=globals())
                fileVersion = Version.fromString(mem["EXPORTER_VERSION"])
                if (
                    fileVersion >= PythonScriptExporter.version()
                    and PythonScriptExporter.displayName() == mem["EXPORTER_NAME"]
                ):
                    pyFlowInstance.newFile()
                    ROOT_GRAPH = pyFlowInstance.graphManager.get().findRootGraph()
                    mem["createScene"](ROOT_GRAPH)
                    pyFlowInstance.afterLoad()

    @staticmethod
    def doExport(pyFlowInstance):

        supportedDataTypes = {"IntPin", "FloatPin", "BoolPin", "StringPin", "ExecPin"}
        supportedStructures = {StructureType.Single}

        script = "# -*- coding: utf-8 -*-\n\n"
        script += "# This file was auto-generated by PyFlow exporter '{0} v{1}'\n".format(
            PythonScriptExporter.displayName(), str(PythonScriptExporter.version())
        )
        script += "#\tCreated: {0}\n\n".format(
            PythonScriptExporter.creationDateString()
        )
        script += "EXPORTER_NAME = '{}'\n".format(PythonScriptExporter.displayName())
        script += "EXPORTER_VERSION = '{}'\n\n".format(
            str(PythonScriptExporter.version())
        )

        rootGraph = pyFlowInstance.graphManager.get().findRootGraph()

        if len(rootGraph.getNodesList()) == 0:
            QMessageBox.warning(pyFlowInstance, "Warning", "Nothing to export!")
            return

        try:
            # create root level nodes
            graphScript = ""
            for node in rootGraph.getNodesList():
                graphScript += nodeToScript(
                    node, supportedDataTypes, supportedStructures
                )

            graphScript += "\n# connect pins\n"

            # create connections
            # for node in rootGraph.getNodesList():
            #     for outPin in node.outputs.values():
            #         for inPinName in outPin.linkedTo:
            #             inPin = pyFlowInstance.graphManager.get().findPinByName(inPinName)
            #             graphScript += "{0} = ROOT_GRAPH.graphManager.findPinByName('{1}')\n".format(outPin.getFullName(), outPin.getFullName())
            #             graphScript += "{0} = ROOT_GRAPH.graphManager.findPinByName('{1}')\n".format(inPin.getFullName(), inPin.getFullName())
            #             graphScript += "connectPins({0}, {1})\n".format(outPin.getFullName(), inPin.getFullName())

            wrappedGraphScript = wrapStringToFunctionDef(
                "createScene", graphScript, {"ROOT_GRAPH": None}
            )

            script += wrappedGraphScript + "\n"

            outFilePath, filterString = QFileDialog.getSaveFileName(
                filter=PythonScriptExporter.name_filter
            )
            if outFilePath != "":
                with open(outFilePath, "w") as f:
                    f.write(script)
            print("saved!")
        except Exception as e:
            QMessageBox.warning(pyFlowInstance, "Warning", str(e))
