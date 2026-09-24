import React from "react";
import { createRoot } from "react-dom/client";
import { useEffect, useState } from "react";
import ResultCard from "./resultcard";
import FilterInput from "./filterinput";
import History from "./history";

function getPathParams(history, path) {
    const choices = [];

    if (path.length === 0) {
        return [{"type":"title", "value":""}];
    }

    let branch = history[path[0]];
    choices.push({
        type: branch.type,
        value: branch.value
    });

    for (let i = 1; i < path.length; i++) {
        branch = branch.branches[path[i]];

        choices.push({
            type: branch.type,
            value: branch.value
        });
    }

    return choices;
}

function SearchFilter (){
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState("");
    const [curParam, setCurParam] = useState({});
    const [curPath, setPath] = useState([]);
    const [history, setHistory] = useState([]);

    function finishLoading(data) {
        setResults( data );
        setLoading( "hidden" );
    }

    function newFilter(param) {
        const newBranch = {
            type: param.type,
            value: param.value,
            branches: []
        };

        if (curPath.length === 0) {
            const newIndex = history.length;

            setHistory(prevHistory => [
                ...prevHistory,
                newBranch
            ]);

            setPath([newIndex]);
            setCurParam(param);
            return;
        }

        const newHistory = structuredClone(history);

        let branch = newHistory[curPath[0]];

        for (let depth = 1; depth < curPath.length; depth++) {
            branch = branch.branches[curPath[depth]];
        }

        const newIndex = branch.branches.length;

        branch.branches.push(newBranch);

        setHistory(newHistory);
        setPath([...curPath, newIndex]);
        setCurParam(param);
    }


    function updatePath(pathToChange) {
        setPath(pathToChange);

        let choices = getPathParams(history, pathToChange);
        setCurParam({"type":"branch", choices});
        
        return;
    }

    useEffect(() => {
        const searchParams = new URLSearchParams(window.location.search);
        fetch(`/api/lookup?${searchParams.toString()}`)
            .then(res => res.json())
            .then(data => finishLoading(data));
        }, []);

    return (
        <div class="centered-block" id="centered-block">
            <div class="left-block">
                <History update={updatePath} path={curPath} history={history} />
            </div>
            <div class="middle-block">
                <FilterInput newParam={ newFilter } />
                <div class="results-block">
                    <div id="loading-results" class={`loading ${ loading }`}>
                        Loading Candidates...
                    </div>
                    <div id="results">
                        { results.map((result, index) => (
                            <ResultCard data={result} index={index} curParam={curParam}/>
                        )) }
                    </div>
                </div>
            </div>
            <div class="right-block">
            </div>
        </div>
    )
}

const element = document.getElementById("container");

if (element) {
    createRoot(element).render(<SearchFilter />);
}
