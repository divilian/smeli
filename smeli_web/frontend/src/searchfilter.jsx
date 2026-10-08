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

function matchesParam(data, param) {
    if (param.type === "branch") {
        return param.choices.every(choice => matchesParam(data, choice));
    }

    if (!(param.type in data) || data[param.type] == null) {
        return true;
    }

    const rawValue = param.value;
    const check = data[param.type];

    if (rawValue.includes(">=")) {
        let value = rawValue.substring( rawValue.indexOf(">=") + 2 ).trim(); 
        return check >= value;
        //return check >= rawValue.split(" ", 2)[1];
    }

    if (rawValue.includes("<=")) {
        let value = rawValue.substring( rawValue.indexOf("<=") + 2 ).trim(); 
        return check <= value;
        //return check <= rawValue.split(" ", 2)[1];
    }

    if (rawValue.includes(">")) {
        let value = rawValue.substring( rawValue.indexOf(">") + 1 ).trim(); 
        return check > value;
        //return check > rawValue.split(" ", 2)[1];
    }

    if (rawValue.includes("<")) {
        let value = rawValue.substring( rawValue.indexOf("<") + 1 ).trim(); 
        return check < value;
        //return check < rawValue.split(" ", 2)[1];
    }

    return data[param.type]
        .toString()
        .toLowerCase()
        .includes(rawValue.toLowerCase());
}

function PageButton({setPage, pageNum}) {
    

    return (
        <button class="pagination-button" onClick={() => setPage(pageNum)}>{pageNum + 1}</button>
    );
}

function SearchFilter (){
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState("");
    //const [curParam, setCurParam] = useState({});
    const [curPath, setPath] = useState([]);
    const [history, setHistory] = useState([]);
    const [page, setPage] = useState(0);
    const [numShown, setNumShown] = useState(0);
    const [pageCount, setPageCount] = useState(0);
    const [shownCards, setShownCards] = useState([]);

    const PAGE_LENGTH = 10;

    function finishLoading(data) {
        for (let i = 0; i < data.length; i++ ){
            data[i]['index'] = i;
        }
        setResults( data );
        setShownCards( data );
        setLoading( "hidden" );
        setNumShown( data.length );
        setPageCount( Math.ceil(data.length / PAGE_LENGTH) );
    }

    function reviewShown(param) {
        let updatedShown = [];
        let workingList = [];
        if (param.type === "branch") {
            workingList = results;
        }
        else {
            workingList = shownCards
        }
        for (let i = 0; i < workingList.length; i++ ){
            if ( matchesParam( workingList[i], param ) ) {
                updatedShown.push( workingList[i] );
            }
        }
        setNumShown( updatedShown.length );
        let updatePC = Math.ceil(updatedShown.length / PAGE_LENGTH);
        setPageCount( updatePC );
        setPage( Math.min( updatePC, page ) ); 
        setShownCards( updatedShown );
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
            reviewShown(param);
            //setCurParam(param);
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
        //setCurParam(param);
        reviewShown(param);
    }


    function updatePath(pathToChange) {
        setPath(pathToChange);

        let choices = getPathParams(history, pathToChange);
        //setCurParam({"type":"branch", choices});
        reviewShown({"type":"branch", choices});
        
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
                        {Array.from({ length: PAGE_LENGTH }, (_) => (
                            <div className="skeleton-card">
                                <div className="skeleton-title">
                                    <span className="skeleton-title-index"></span>
                                    <span className="skeleton-title-title"></span>
                                </div>

                                <div className="result-authors">
                                    <span className="skeleton-authors"></span>
                                    <span className="skeleton-date"></span>
                                </div>

                                <div className="skeleton-extra">
                                    <p><span className="skeleton-extra-key"></span></p>
                                    <p><span className="skeleton-extra-key"></span></p>
                                    <p><span className="skeleton-extra-key"></span></p>
                                </div>
                            </div>
                        ))}
                    </div>
                    <div id="results">
                        { /*results*/ shownCards.map((result, index) => (
                            <ResultCard data={result} index={index} /*curParam={curParam}*/ page={page} pageLength={PAGE_LENGTH}/>
                        )) }
                        { shownCards.length == 0 && loading !== "" ? (
                            <div class={`loading`}>
                                No results found.
                            </div>
                        ) : (null)}
                    </div>
                    <div id="pagination" class="pagination">
                        {Array.from({ length: pageCount }, (_, pageNum) => (
                            <PageButton
                                key={ pageNum}
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
