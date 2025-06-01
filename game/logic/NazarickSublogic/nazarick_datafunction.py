from typing import List, Optional, Tuple, Dict, Any
from game import models


def howManyStepNeeded(pos1: models.Position, pos2: models.Position) -> int:
    return abs(pos1.x - pos2.x) + abs(pos1.y - pos2.y)


def getPositionAsDict(positionObj: models.Position) -> Dict[str, int]:
    return {"x": positionObj.x, "y": positionObj.y}


def getPropertiesAsDict(
    propsObj: Optional[models.Properties],
) -> Optional[Dict[str, Any]]:
    if not propsObj:
        return None
    baseAsDict = getPositionAsDict(propsObj.base) if propsObj.base else None
    return {
        "points": propsObj.points,
        "pair_id": propsObj.pair_id,
        "diamonds": propsObj.diamonds,
        "score": propsObj.score,
        "name": propsObj.name,
        "inventory_size": propsObj.inventory_size,
        "can_tackle": propsObj.can_tackle,
        "milliseconds_left": propsObj.milliseconds_left,
        "time_joined": propsObj.time_joined,
        "base": baseAsDict,
    }


def getGameObjectAsDict(gameObj: models.GameObject) -> Dict[str, Any]:
    return {
        "id": gameObj.id,
        "position": getPositionAsDict(gameObj.position),
        "type": gameObj.type,
        "properties": getPropertiesAsDict(gameObj.properties),
    }


def getDiamondDataAsDict(diamondObj: models.GameObject) -> Dict[str, Any]:
    points = 0
    if diamondObj.properties and diamondObj.properties.points is not None:
        points = diamondObj.properties.points
    return {"position": getPositionAsDict(diamondObj.position), "points": points}


def getTeleporterDataAsDict(teleporterObj: models.GameObject) -> Dict[str, Any]:
    return getGameObjectAsDict(teleporterObj)


def getDiamondButtonDataAsDict(buttonObj: models.GameObject) -> Dict[str, Any]:
    return getGameObjectAsDict(buttonObj)


def calculateDiamondDensity(
    diamond: models.GameObject, botPos: models.Position
) -> float:
    if (
        not diamond.properties
        or diamond.properties.points is None
        or diamond.properties.points == 0
    ):
        return 0.0

    steps = howManyStepNeeded(botPos, diamond.position)
    if steps == 0:
        return float("inf")
    return diamond.properties.points / steps


def determineTargetAndExitTeleporters(
    allTeleporterObjects: List[models.GameObject], currentPos: models.Position
) -> Tuple[Optional[models.GameObject], Optional[models.GameObject], int]:
    if not allTeleporterObjects:
        return None, None, float("inf")

    sortedTeleporters = sorted(
        allTeleporterObjects,
        key=lambda tpObj: howManyStepNeeded(currentPos, tpObj.position),
    )

    if not sortedTeleporters:
        return None, None, float("inf")

    targetTeleporterObj = sortedTeleporters[0]
    distanceToTargetTeleporter = howManyStepNeeded(
        currentPos, targetTeleporterObj.position
    )

    exitTeleporterObj: Optional[models.GameObject] = None

    if targetTeleporterObj.properties and targetTeleporterObj.properties.pair_id:
        targetPairIdStr = targetTeleporterObj.properties.pair_id
        for tpObj in allTeleporterObjects:
            if str(tpObj.id) == targetPairIdStr and tpObj.id != targetTeleporterObj.id:
                exitTeleporterObj = tpObj
                break

    if exitTeleporterObj is None and len(allTeleporterObjects) == 2:
        if targetTeleporterObj == allTeleporterObjects[0]:
            exitTeleporterObj = allTeleporterObjects[1]
        else:
            exitTeleporterObj = allTeleporterObjects[0]

    return targetTeleporterObj, exitTeleporterObj, distanceToTargetTeleporter


def decideBestDensityGoal(
    diamondObjects: List[models.GameObject],
    botPos: models.Position,
    targetTeleporterObj: Optional[models.GameObject],
    exitTeleporterObj: Optional[models.GameObject],
    distanceToTargetTeleporter: int,
) -> Optional[models.Position]:
    if not diamondObjects:
        return None

    bestDirectDensity = -1.0
    bestDirectTargetPos: Optional[models.Position] = None

    for diamondObj in diamondObjects:
        density = calculateDiamondDensity(diamondObj, botPos)
        if density > bestDirectDensity:
            bestDirectDensity = density
            bestDirectTargetPos = diamondObj.position

    bestTeleportDensity = -1.0
    bestTeleportTargetPos: Optional[models.Position] = None

    if (
        targetTeleporterObj
        and exitTeleporterObj
        and distanceToTargetTeleporter != float("inf")
    ):
        for diamondObj in diamondObjects:
            if not diamondObj.properties or diamondObj.properties.points is None:
                continue

            stepsFromExitToDiamond = howManyStepNeeded(
                exitTeleporterObj.position, diamondObj.position
            )
            totalStepsViaTeleport = (
                distanceToTargetTeleporter + 1 + stepsFromExitToDiamond
            )

            if totalStepsViaTeleport == 0:
                densityViaTeleport = float("inf")
            else:
                densityViaTeleport = (
                    diamondObj.properties.points / totalStepsViaTeleport
                )

            if densityViaTeleport > bestTeleportDensity:
                bestTeleportDensity = densityViaTeleport
                bestTeleportTargetPos = targetTeleporterObj.position

    if bestDirectTargetPos is None and bestTeleportTargetPos is None:
        return None
    elif bestDirectTargetPos is None:
        return bestTeleportTargetPos
    elif bestTeleportTargetPos is None:
        return bestDirectTargetPos
    elif bestDirectDensity >= bestTeleportDensity:
        return bestDirectTargetPos
    else:
        return bestTeleportTargetPos
