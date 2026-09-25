import React from "react";
import { useEffect, useState } from "react";

export default function History({ update, path, history }) {

    function renderBranch(branch, curPath) {
        const chosen = curPath.every((value, i) => value === path[i]) ? "choosen" : "";

        return (
            <div>
                <div class={`branch ${chosen}`} data-depth={curPath.length + 1} onClick={() => update(curPath)}>
                    {`|-`} {branch.type}: {branch.value}
                </div>

                <div>
                    {branch.branches.map((child, index) => (
                        <div>
                            {renderBranch(child, [...curPath, index])}
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div>
            <div class="branch bold choosen" data-depth="1" onClick={() => update([])}>
                Initial Search
            </div>
            {history.map((branch, index) => (
                <div>
                    {renderBranch(branch, [index])}
                </div>
            ))}
        </div>
    );
}

