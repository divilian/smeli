import React from "react";
import { useEffect, useState } from "react";

export default function History({ update, path, history }) {

    /*
    function renderBranch(branch, curPath) {
        const chosen = curPath.every((value, i) => value === path[i]) ? "choosen" : "";

        return (
            <div>
                <div class={`branch ${chosen}`} >
                    {`|-`} {branch.type}: {branch.value}
                </div>

                <div>
                    <p>|</p>
                    {branch.branches.map((child, index) => (
                        <div>
                            {renderBranch(child, [...curPath, index])}
                        </div>
                    ))}
                </div>
            </div>
        );
    }*/
    //<p>|</p>
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

    function renderPath(path, history, index) {
        return;
       /* if (index >= path.length) {
            return;
        }
        return (
            <>
                <p>|</p>
                <p>{history[branches][path[index]]['type']}</p>
                {renderPath(path, history[branches][path[index]], index + 1 )}
            </>
        );*/
    }
//{renderPath(path, history, 0)}
    return (
        <div>
            <div class="branch bold choosen" data-depth="1" onClick={() => update([])}>
                Initial Search
            </div>
            <div class="previous-paths">
                {history.map((branch, index) => (
                    <div>
                        {renderBranch(branch, [index])}
                    </div>
                ))}
            </div>
        </div>
    );
}

