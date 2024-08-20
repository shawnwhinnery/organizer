#Author-
#Description-

import adsk.core, adsk.fusion, adsk.cam, traceback

LAYOUT = {
    "type": "row",  # row, column, cell
    "cells": [
                {
                    "type": "column",
                    "cells": [
                        {"type": "drawer"},
                        {"type": "drawer"},
                        {"type": "drawer"},
                    ]
                },
                {
                    "type": "column",
                    "cells": [
                        {"type": "drawer"},
                        {"type": "drawer"},
                    ]
                },
                {
                    "type": "column",
                    "cells": [
                        {"type": "drawer"},
                    ]
                },
            ]
}

NOZLE_DIAMETER = 0.04
GAP = NOZLE_DIAMETER * 3
DRAWER_SHELF_GAP = NOZLE_DIAMETER * 2
WIDTH = 26
HEIGHT = 15
DEPTH = 9
THUMB_RADIUS = 1.8


def gapRect(rect, gap=GAP):
    return {
        "x": rect["x"] + gap, 
        "y": rect["y"] + gap,
        "width": rect["width"] - (gap * 2),
        "height": rect["height"] - (gap * 2)
        }

# Draw a rectangle using a bounding box
def drawRect(lines, rect):
    left_bottom = adsk.core.Point3D.create(rect["x"], rect["y"], 0)
    left_top = adsk.core.Point3D.create(rect["x"], rect["y"] + rect['height'], 0)
    lines.addByTwoPoints(left_bottom, left_top)
    
    top_left = left_top
    top_right = adsk.core.Point3D.create(rect["x"] + rect["width"], rect["y"] + rect['height'], 0)
    lines.addByTwoPoints(top_left, top_right)
    
    right_top = top_right
    right_bottom = adsk.core.Point3D.create(rect["x"] + rect["width"], rect["y"], 0)
    lines.addByTwoPoints(right_top, right_bottom)
    
    bottom_right = right_bottom
    bottom_left = left_bottom
    lines.addByTwoPoints(bottom_right, bottom_left)


def extrudeRect(rootComp, sketch, depth = DEPTH, i=0):
    # Get the profile defined by the rectangle
    prof = sketch.profiles.item(i)  # Assuming only one profile is created

    # Create an extrusion input to define the extrusion
    extrudes = rootComp.features.extrudeFeatures
    extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

    # Define the distance to extrude
    distance = adsk.core.ValueInput.createByReal(depth)  # Extrude by 2 cm (or inches depending on units)
    extInput.setDistanceExtent(False, distance)

    # Create the extrusion
    return extrudes.add(extInput)

def getFrontFace(ext):
    # Define the target normal vector for the front face (positive Y direction)
    target_vector = adsk.core.Vector3D.create(0, -1, 0)

    # Find the face that is closest to pointing in the positive Y direction
    front_face = None
    max_dot_product = -2  # Start with a value less than the minimum possible dot product (-1)
    
    for face in ext.faces:
        # Get the normal vector of the face
        _, normal_vector = face.evaluator.getNormalAtPoint(face.pointOnFace)
        
        # Calculate the dot product between the face normal and the target vector
        dot_product = normal_vector.dotProduct(target_vector)
        
        # Check if this face is closer to the front direction
        if dot_product > max_dot_product:
            max_dot_product = dot_product
            front_face = face
    return front_face

def getTopFace(ext):
    # Define the target normal vector for the top face (positive Z direction)
    target_vector = adsk.core.Vector3D.create(0, 0, 1)

    # Find the face that is closest to pointing in the positive Z direction
    top_face = None
    max_dot_product = -2  # Start with a value less than the minimum possible dot product (-1)
    
    for face in ext.faces:
        # Get the normal vector of the face
        _, normal_vector = face.evaluator.getNormalAtPoint(face.pointOnFace)
        
        # Calculate the dot product between the face normal and the target vector
        dot_product = normal_vector.dotProduct(target_vector)
        
        # Check if this face is closer to the top direction
        if dot_product > max_dot_product:
            max_dot_product = dot_product
            top_face = face
    return top_face

def run(context):
    ui = None

    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        design = app.activeProduct
        rootComp = design.rootComponent
        extrudes = rootComp.features.extrudeFeatures
        
        # Create a new sketch on the X-Y plane.
        sketches = rootComp.sketches
        xyPlane = rootComp.xYConstructionPlane
        # 
        shelfWallsSketch = sketches.add(xyPlane)
        shelfLines = shelfWallsSketch.sketchCurves.sketchLines

        # Produces the floor plan of the shelf
        # This includes the walls
        def draw(cell, rect=None):
            
            # We know the root cell because it has no rect
            isRootCell = rect == None
            
            cellRect = None
            if isRootCell:
                cellRect = {"x": 0, "y": 0, "width": WIDTH, "height": HEIGHT}
            else:
                cellRect = rect
            
            # Draw the root cell and drawers
            if isRootCell:
                drawRect(shelfLines, cellRect)
                ext = extrudeRect(rootComp, shelfWallsSketch, GAP * -1, 0)
                cellRect = gapRect(cellRect)
            if cell["type"] == "drawer":
                drawerRect = gapRect(cellRect, DRAWER_SHELF_GAP)

                # add a slot to the shelf
                drawRect(shelfLines, cellRect)
                # Create a dedicated sketch for the drawer because it will be extruded
                drawerSketch = sketches.add(xyPlane)
                drawerLines = drawerSketch.sketchCurves.sketchLines
                # Draw the drawer
                drawRect(drawerLines, drawerRect)
                
                # Create the drawer
                ext = extrudeRect(rootComp, drawerSketch, DEPTH)

                #carve out the drawer
                
                # Get the top face of the extruded body
                frontFace = getFrontFace(ext)  # Adjust the index if needed to select the correct face

                # Create a new sketch on the top face
                sketch2 = sketches.add(frontFace)
                innerLines = sketch2.sketchCurves.sketchLines

                # Create the inner rectangle (cutting profile)
                drawRect(innerLines, {
                    "x": drawerRect["x"] + GAP,
                    "y": GAP,
                    "width": drawerRect["width"] - GAP * 2,
                    "height": DEPTH - GAP * 2
                })

                # Get the cutting profile and extrude it to cut the body
                prof = sketch2.profiles.item(1)  # Assuming only one profile is created

                # Create an extrusion input to define the extrusion
                extrudes = rootComp.features.extrudeFeatures
                extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.CutFeatureOperation)

                # Define the distance to extrude
                distance = adsk.core.ValueInput.createByReal((-1 * drawerRect["height"]) + GAP)
                extInput.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(distance), adsk.fusion.ExtentDirections.PositiveExtentDirection)

                # Create the extrusion
                extrudes.add(extInput)
                
                # Cut out a thumb hole for the drawer
                topFace = getTopFace(ext)
                topSketch = sketches.add(topFace)
                
                circles = topSketch.sketchCurves.sketchCircles
                circles.addByCenterRadius(
                    # Center of the drawer
                    adsk.core.Point3D.create(
                        drawerRect["x"] + (drawerRect["width"] / 2), 
                        drawerRect['y'], 
                        0
                    ),
                    THUMB_RADIUS
                )
                
                for line in topSketch.sketchCurves.sketchLines:
                    line.deleteMe()
                
                # Get the cutting profile and extrude it to cut the body
                holeProf = topSketch.profiles.item(0)  # Assuming only one profile is created

                # Create an extrusion input to define the extrusion
                holeExtInput = extrudes.createInput(holeProf, adsk.fusion.FeatureOperations.CutFeatureOperation)

                # Define the distance to extrude
                holeDistance = adsk.core.ValueInput.createByReal(-1)  # Extrude by 5 units
                holeExtInput.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(holeDistance), adsk.fusion.ExtentDirections.PositiveExtentDirection)

                # Create the extrusion
                extrudes.add(holeExtInput)
                
            
            # compute child layout, render children
            if "cells" in cell:
                if cell["type"] == "row":
                    i = 0
                    totalGap = GAP * (len(cell["cells"]) - 1)
                    childWidth = (cellRect["width"] - totalGap) / len(cell["cells"])
                    childHeight = cellRect["height"]
                    childY = cellRect["y"]
                    
                    for childCell in cell["cells"]:
                        # Calculate the child rect
                        childX = cellRect["x"] + (i * childWidth)
                        
                        isFirstChild = i == 0
                        if not isFirstChild:
                            childX += GAP * i

                        draw(childCell, {
                            "x": childX,
                            "y": childY,
                            "width": childWidth,
                            "height": childHeight
                        })
                        i += 1
                if cell["type"] == "column":
                    i = 0
                    totalGap = GAP * (len(cell["cells"]) - 1)
                    childWidth = cellRect["width"]
                    childHeight = (cellRect["height"] - totalGap) / len(cell["cells"])
                    childX = cellRect["x"]
                    
                    for childCell in cell["cells"]:
                        # Calculate the child rect
                        childY = cellRect["y"] + (i * childHeight)
                        
                        isFirstChild = i == 0
                        if not isFirstChild:
                            childY += GAP * i

                        draw(childCell, {
                            "x": childX,
                            "y": childY,
                            "width": childWidth,
                            "height": childHeight
                        })
                        i += 1

        draw(LAYOUT)
        
        extrudeRect(rootComp, shelfWallsSketch, DEPTH, 0)
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
