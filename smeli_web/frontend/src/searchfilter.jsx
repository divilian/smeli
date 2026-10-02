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

function PageButton({setPage, pageNum}) {
    

    return (
        <button class="pagination-button" onClick={() => setPage(pageNum)}>{pageNum + 1}</button>
    );
}

function SearchFilter (){
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState("");
    const [curParam, setCurParam] = useState({});
    const [curPath, setPath] = useState([]);
    const [history, setHistory] = useState([]);
    const [page, setPage] = useState(0);
    const [numShown, setNumShown] = useState(0);
    const [pageCount, setPageCount] = useState(0);

    const PAGE_LENGTH = 10;

    function finishLoading(data) {
        setResults( data );
        setLoading( "hidden" );
        setNumShown( data.length );
        setPageCount( Math.ceil(data.length / PAGE_LENGTH) );
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

        console.log(newHistory);
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
                <div class="history-container">
                    <p>Filter History</p>
                    <History update={updatePath} path={curPath} history={history} />
                </div>
            </div>
            <div class="middle-block">
                <FilterInput newParam={ newFilter } />
                <div class="results-block">
                    <div id="loading-results" class={`loading ${ loading }`}>
                        Loading Candidates...
                    </div>
                    <div id="results">
                        { results.map((result, index) => (
                            <ResultCard data={result} index={index} curParam={curParam} page={page} pageLength={PAGE_LENGTH}/>
                        )) }
                    </div>
                    <div id="pagination" class="pagination">
                        {Array.from({ length: pageCount }, (_, pageNum) => (
                            <PageButton
                                key={pageNum}
                                setPage={setPage}
                                pageNum={pageNum}
                            />
                        ))}
                    </div>
                </div>
            </div>
            <div class="right-block">
                <div class="filter-instructions">
                    <h3>Filtering Instructions:</h3>
                    <p>Enter criteria into the input field and hit "Enter" or press "Add Criteria" button. Up and Down arrow keys can be used to quickly switch criteria being added.</p>
                    <p>Filtering is case in-sensitive and currently supports a few comparing operations. These must be used at the beginning and have a space in between them and the criteria:</p>
                    <ul>
                        <li>{"<"}</li>
                        <li>{"<="}</li>
                        <li>{">"}</li>
                        <li>{">="}</li>
                    </ul>
                    <p>These work best with number based fields, but do technically work with any field.</p>
                    <h3>Branching Instructions:</h3>
                    <p>On the left part of the page, you will see all the filters you have put in and what filters they built off of.</p>
                    <p>When adding a criteria, all previous criteria on the branch you are on are also checked, so staying on a branch means you can only narrow your search, not expand.</p>
                    <p>By clicking on a past filter, you are brought to a previous collection of results. You can use this context to narrow your search in a different direction.</p>
                </div>
            </div>
        </div>
    )
}

const element = document.getElementById("container");

if (element) {
    createRoot(element).render(<SearchFilter />);
}
